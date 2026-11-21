"""Synthetic contract/image-input tests. Does not run or validate neural networks."""
import copy
import unittest
from PIL import Image
from ai.src.vision.vietfood_adapter import validate_output, FoodAdapter, SUPPORTED
from jsonschema import ValidationError, Draft202012Validator
import json
from pathlib import Path

def example():
    return {'schema_version':'1.0.0','request_id':'test-1','created_at':'2026-11-15T00:00:00+00:00',
        'model':{'recognition_sha256':'a'*64,'portion_sha256':'b'*64,'release_status':'experimental'},
        'image':{'width':640,'height':480,'color_space':'RGB','sha256_rgb':'c'*64,'coordinate_system':'pixels_after_exif_orientation'},
        'policy':{'confidence_threshold':0.6494140625,'supported_class_ids':SUPPORTED,'mass_aggregation':'none'},
        'detections':[{'detection_id':'det_0000','dataset_class_id':34,'label':'Hamburger','confidence':0.91,
          'bbox_xyxy':[10.,20.,300.,400.],'kb_food_id':None,'kb_mapping_status':'not_resolved',
          'portion':{'estimated_mass_g':861.28,'unit':'g','method':'foodcnn_v2','scope':'padded_detection_crop',
                     'status':'unvalidated_estimate','consumed_mass_g':None,'requires_user_review':True}}],
        'foods':[{'dataset_class_id':34,'label':'Hamburger','confidence':0.91,
                  'confidence_aggregation':'maximum_detection_score','detection_ids':['det_0000'],
                  'kb_food_id':None,'kb_mapping_status':'not_resolved'}],
        'nutrition_status':'not_computed','warnings':['PORTION_UNVALIDATED','KB_MAPPING_UNRESOLVED']}

class ContractTests(unittest.TestCase):
    def test_schema_valid(self):
        schema_path = Path(__file__).resolve().parents[2] / 'src/vision/response.schema.json'
        schema = json.loads(schema_path.read_text(encoding='utf-8'))
        Draft202012Validator.check_schema(schema)
    def test_valid_and_empty(self):
        validate_output(example())
        p=example(); p['detections']=[]; p['foods']=[]; validate_output(p)
    def test_reject_invalid_mass_states(self):
        for value in [0,-10,float('nan'),float('inf'),None]:
            p=example(); p['detections'][0]['portion']['estimated_mass_g']=value
            with self.assertRaises((ValueError,ValidationError)): validate_output(p)
        p=example(); p['detections'][0]['portion'].update(estimated_mass_g=None,status='invalid_prediction')
        validate_output(p)
    def test_box_bounds(self):
        for box in [[0,0,641,400],[20,20,10,30],[0,0,100,481]]:
            p=example(); p['detections'][0]['bbox_xyxy']=box
            with self.assertRaises(ValueError): validate_output(p)
    def test_group_reference_and_confidence(self):
        p=example(); p['foods'][0]['detection_ids']=['det_9999']
        with self.assertRaises(ValueError): validate_output(p)
        p=example(); p['foods'][0]['confidence']=0.8
        with self.assertRaises(ValueError): validate_output(p)
    def test_duplicate_detection(self):
        p=example(); p['detections'].append(copy.deepcopy(p['detections'][0]))
        with self.assertRaises(ValueError): validate_output(p)
    def test_unsupported_class_and_consumed(self):
        p=example(); p['detections'][0]['dataset_class_id']=27
        with self.assertRaises(ValidationError): validate_output(p)
        p=example(); p['detections'][0]['portion']['consumed_mass_g']=100
        with self.assertRaises(ValidationError): validate_output(p)
    def test_unknown_fields(self):
        p=example(); p['fake_mass_confidence']=0.99
        with self.assertRaises(ValidationError): validate_output(p)
    def test_exif_and_transparency_and_limits(self):
        adapter=object.__new__(FoodAdapter); adapter.max_pixels=1000
        img=Image.new('RGB',(20,10)); exif=img.getexif(); exif[274]=6; img.info['exif']=exif.tobytes()
        self.assertEqual(adapter._image(img).size,(10,20))
        self.assertEqual(adapter._image(Image.new('RGBA',(2,2),(0,0,0,0))).getpixel((0,0)),(255,255,255))
        with self.assertRaises(ValueError): adapter._image(Image.new('RGB',(100,100)))
        with self.assertRaises(TypeError): adapter._image([1,2,3])

if __name__=='__main__': unittest.main()
