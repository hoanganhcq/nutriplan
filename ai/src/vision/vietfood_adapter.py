"""VietFood response contract 1.0.0; portion model remains experimental."""
from pathlib import Path
from datetime import datetime, timezone
from io import BytesIO
import hashlib
import json
import math
import uuid

VERSION = "1.0.0"
SUPPORTED = sorted(set(range(68)) - {20, 27, 29, 30, 32, 42, 49, 50, 52, 55, 56})


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def local_file(root, name):
    root = Path(root).resolve()
    path = (root / name).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError(f"File missing or outside package: {name}")
    return path


def validate_output(result, schema_path=None):
    from jsonschema import Draft202012Validator, FormatChecker
    schema_path = schema_path or Path(__file__).parent / "response.schema.json"
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    # JSON Schema alone may accept nonfinite Python floats; enforce valid JSON.
    json.dumps(result, allow_nan=False)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(result)
    width, height = result["image"]["width"], result["image"]["height"]
    ids = set()
    grouped = {}
    for detection in result["detections"]:
        did = detection["detection_id"]
        if did in ids:
            raise ValueError("Duplicate detection ID")
        ids.add(did)
        x1, y1, x2, y2 = detection["bbox_xyxy"]
        if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
            raise ValueError("Bounding box outside oriented image")
        grouped.setdefault(detection["dataset_class_id"], []).append(detection)
    foods = {food["dataset_class_id"]: food for food in result["foods"]}
    if len(foods) != len(result["foods"]) or set(foods) != set(grouped):
        raise ValueError("Food groups do not match detections")
    for cid, detections in grouped.items():
        food = foods[cid]
        if set(food["detection_ids"]) != {d["detection_id"] for d in detections}:
            raise ValueError("Invalid grouped detection references")
        if any(d["label"] != food["label"] for d in detections):
            raise ValueError("Grouped labels differ")
        if food["confidence"] != max(d["confidence"] for d in detections):
            raise ValueError("Grouped confidence must be maximum detection score")
    return result


def make_mass_model():
    from torch import nn

    class DeepWeightCNN(nn.Module):
        def __init__(self):
            super().__init__()
            layers = []
            channels = [3, 32, 64, 128, 256]
            for cin, cout in zip(channels[:-1], channels[1:]):
                layers.extend([
                    nn.Conv2d(cin, cout, 3, padding=1),
                    nn.BatchNorm2d(cout), nn.ReLU(), nn.MaxPool2d(2),
                ])
            layers.append(nn.AdaptiveAvgPool2d((1, 1)))
            self.features = nn.Sequential(*layers)
            self.regressor = nn.Sequential(
                nn.Flatten(), nn.Linear(256, 128), nn.BatchNorm1d(128),
                nn.ReLU(), nn.Dropout(0.3), nn.Linear(128, 64),
                nn.BatchNorm1d(64), nn.ReLU(), nn.Dropout(0.2), nn.Linear(64, 1),
            )

        def forward(self, value):
            return self.regressor(self.features(value))

    return DeepWeightCNN()


class FoodAdapter:
    """Load once, call predict sequentially. Inputs: file path, bytes or PIL image.

    No automatic KB mapping, nutrition computation or aggregation of crop masses.
    """

    def __init__(self, package_dir, device=None, max_pixels=40_000_000):
        import torch
        from torchvision import transforms
        from ultralytics import YOLO

        self.root = Path(package_dir).resolve()
        self.config = json.loads(local_file(self.root, "config.json").read_text())
        self.manifest = json.loads(local_file(self.root, "manifest.json").read_text())
        entries = {entry["path"]: entry for entry in self.manifest["files"]}
        recognition = self.config["recognition"]
        portion = self.config["portion"]
        required = ["config.json", "classes.json", recognition["weights"], portion["weights"]]
        for name in required:
            path = local_file(self.root, name)
            entry = entries.get(name)
            if not entry or sha256_file(path) != entry["sha256"] or path.stat().st_size != entry["bytes"]:
                raise ValueError(f"Integrity check failed: {name}")
        settings = recognition["inference"]
        if (sorted(recognition["supported_class_ids"]) != SUPPORTED
                or settings["output_confidence"] != 0.6494140625
                or settings["initial_confidence"] != 0.01
                or settings["nms_iou"] != 0.7
                or settings["agnostic_nms"] is not False
                or settings["max_det"] != 300
                or recognition["preprocessing"]["imgsz"] != 640
                or recognition["preprocessing"]["rect"] is not False
                or settings["augment"] is not False
                or portion["architecture"] != "DeepWeightCNN"
                or portion["state_dict_key"] != "model_state_dict"
                or portion["preprocessing"]["padding_each_side_fraction"] != 0.05
                or portion["preprocessing"]["resize_hw"] != [224, 224]
                or portion["preprocessing"]["normalization"] is not None
                or portion["output_scaling"] != 1.0):
            raise ValueError("Unsupported policy: this adapter requires the documented V1 configuration")
        self.device = torch.device(device or ("cuda:0" if torch.cuda.is_available() else "cpu"))
        if self.device.type not in {"cpu", "cuda"}:
            raise ValueError("Use cpu or cuda:N")
        self.max_pixels = int(max_pixels)
        self.detector = YOLO(str(self.root / recognition["weights"]))
        labels = json.loads((self.root / "classes.json").read_text())
        names = {int(row["dataset_class_id"]): row["label"] for row in labels}
        if len(labels) != 68 or set(names) != set(range(68)) or dict(self.detector.names) != names:
            raise ValueError("Class names/order mismatch")
        self.mass = make_mass_model().to(self.device)
        checkpoint = torch.load(self.root / portion["weights"], map_location="cpu", weights_only=True)
        self.mass.load_state_dict(checkpoint["model_state_dict"], strict=True)
        self.mass.eval()
        self.transform = transforms.Compose([transforms.Resize((224, 224)), transforms.ToTensor()])
        self.model_info = {
            "recognition_sha256": entries[recognition["weights"]]["sha256"],
            "portion_sha256": entries[portion["weights"]]["sha256"],
            "release_status": "experimental",
        }

    def _image(self, source):
        from PIL import Image, ImageOps
        if isinstance(source, Image.Image):
            opened = source
            close = False
        elif isinstance(source, (str, Path, bytes, bytearray)):
            opened = Image.open(BytesIO(source) if isinstance(source, (bytes, bytearray)) else source)
            close = True
        else:
            raise TypeError("Expected image path, encoded image bytes or PIL image; NumPy/BGR is not accepted")
        try:
            if opened.width * opened.height > self.max_pixels:
                raise ValueError("Image exceeds pixel limit")
            if getattr(opened, "n_frames", 1) != 1:
                raise ValueError("Use a single still image")
            oriented = ImageOps.exif_transpose(opened)
            if oriented.mode not in {"RGB", "RGBA", "L", "LA", "P"}:
                raise ValueError("Use a standard 8-bit RGB/grayscale image")
            if "A" in oriented.getbands() or "transparency" in oriented.info:
                rgba = oriented.convert("RGBA")
                oriented = Image.alpha_composite(Image.new("RGBA", rgba.size, "white"), rgba)
            return oriented.convert("RGB")
        finally:
            if close:
                opened.close()

    def predict(self, source, request_id=None):
        import torch
        image = self._image(source)
        width, height = image.size
        device = (self.device.index if self.device.index is not None else 0) if self.device.type == "cuda" else "cpu"
        result = self.detector.predict(
            source=image, imgsz=640, rect=False, conf=0.01, iou=0.7,
            agnostic_nms=False, max_det=300, augment=False,
            half=self.device.type == "cuda", device=device, verbose=False,
        )[0]
        warnings = ["PORTION_UNVALIDATED", "KB_MAPPING_UNRESOLVED"]
        if len(result.boxes) >= 300:
            warnings.append("MAX_DETECTIONS_REACHED")
        detections, grouped = [], {}
        with torch.inference_mode():
            for box in result.boxes:
                cid, score = int(box.cls.item()), float(box.conf.item())
                if cid not in SUPPORTED or score < 0.6494140625:
                    continue
                coordinates = list(map(float, box.xyxy[0].cpu().tolist()))
                if not all(math.isfinite(v) for v in coordinates + [score]) or not 0 <= score <= 1:
                    raise ValueError("Nonfinite or invalid detection output")
                x1, y1, x2, y2 = coordinates
                x1, x2 = max(0., min(width, x1)), max(0., min(width, x2))
                y1, y2 = max(0., min(height, y1)), max(0., min(height, y2))
                if x2 <= x1 or y2 <= y1:
                    warnings.append("INVALID_BOX_SKIPPED")
                    continue
                dx, dy = (x2-x1)*0.05, (y2-y1)*0.05
                crop = image.crop((max(0, math.floor(x1-dx)), max(0, math.floor(y1-dy)),
                                   min(width, math.ceil(x2+dx)), min(height, math.ceil(y2+dy))))
                grams = float(self.mass(self.transform(crop).unsqueeze(0).to(self.device)).item())
                valid = math.isfinite(grams) and grams > 0
                if not valid:
                    warnings.append("INVALID_MASS_PREDICTION")
                did = f"det_{len(detections):04d}"
                detection = {
                    "detection_id": did, "dataset_class_id": cid,
                    "label": self.detector.names[cid], "confidence": score,
                    "bbox_xyxy": [x1, y1, x2, y2],
                    "kb_food_id": None, "kb_mapping_status": "not_resolved",
                    "portion": {
                        "estimated_mass_g": grams if valid else None,
                        "unit": "g", "method": "foodcnn_v2",
                        "scope": "padded_detection_crop",
                        "status": "unvalidated_estimate" if valid else "invalid_prediction",
                        "consumed_mass_g": None, "requires_user_review": True,
                    },
                }
                detections.append(detection)
                food = grouped.setdefault(cid, {
                    "dataset_class_id": cid, "label": detection["label"],
                    "confidence": score, "confidence_aggregation": "maximum_detection_score",
                    "detection_ids": [], "kb_food_id": None, "kb_mapping_status": "not_resolved",
                })
                food["confidence"] = max(food["confidence"], score)
                food["detection_ids"].append(did)
        digest = hashlib.sha256(f"RGB:{width}x{height}:".encode() + image.tobytes()).hexdigest()
        payload = {
            "schema_version": VERSION,
            "request_id": request_id if request_id is not None else str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "model": self.model_info.copy(),
            "image": {"width": width, "height": height, "color_space": "RGB", "sha256_rgb": digest,
                      "coordinate_system": "pixels_after_exif_orientation"},
            "policy": {"confidence_threshold": 0.6494140625, "supported_class_ids": SUPPORTED,
                       "mass_aggregation": "none"},
            "detections": detections,
            "foods": [grouped[cid] for cid in sorted(grouped)],
            "nutrition_status": "not_computed", "warnings": sorted(set(warnings)),
        }
        return validate_output(payload)
