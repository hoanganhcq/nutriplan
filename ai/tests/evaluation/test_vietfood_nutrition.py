import unittest, json, copy, hashlib
from ai.src.rag.vietfood_kb import HERE, load_kb, validate, compute_meal, assess_targets, retrieve_clinical, search_foods, prepare_rag, adapter_candidates

class NutritionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  if not (HERE/'data/food_kb.json').is_file():
   raise unittest.SkipTest('Local VietFood composition catalog is unavailable')
  cls.kb=load_kb()
 def request(self,**changes):
  r={'request_id':'test','items':[{'item_id':'rice','food_id':'USDA_FDC_168878','amount':200,'unit':'g','quantity_source':'weighed','food_confirmed':True,'quantity_confirmed':True}], 'period':'meal','day_log_complete':False,'overlap_reviewed':True}
  r.update(changes);return r
 def profile(self,**changes):
  p={'age_years':50,'conditions':['CKD','T2DM','CVD'],'pregnant':False,'kidney_disease_type':'CKD','ckd_stage':'G3b','dialysis':'none','diabetes_type':'type2','transplant':False,'metabolic_instability':False,'frailty_or_malnutrition':False,'sodium_wasting_nephropathy':False,'clinician_daily_targets':[]}
  p.update(changes);return p
 def target(self,**changes):
  t={'nutrient':'energy_kcal','value':2000,'unit':'kcal/day','operator':'<=','source':'user_reported_clinician_plan','confirmed':True,'plan_reference':'fictional test only'};t.update(changes);return t
 def test_root_schema_rejects_unrelated_object(self):
  from jsonschema import Draft202012Validator, ValidationError
  with self.assertRaises(ValidationError):Draft202012Validator(self.kb['schema']).validate({'anything':1})
 def test_schema_and_links(self):self.assertEqual(validate(self.kb)['foods'],150)
 def test_rice_arithmetic(self):self.assertAlmostEqual(compute_meal(self.kb,self.request())['totals']['energy_kcal'],260)
 def test_serving_conversion(self):
  r=self.request();r['items'][0].update(amount=1,unit='reference_serving',quantity_source='reference_default')
  self.assertAlmostEqual(compute_meal(self.kb,r)['totals']['energy_kcal'],205.4)
 def test_missing_not_zero(self):
  r=self.request();food=next(f for f in self.kb['food']['foods'] if f['nutrition']['values']['sodium_mg'] is None)
  second=copy.deepcopy(r['items'][0]);second.update(item_id='second',food_id=food['food_id']);r['items'].append(second)
  out=compute_meal(self.kb,r);self.assertIsNone(out['totals']['sodium_mg']);self.assertEqual(out['completeness']['sodium_mg']['missing_item_ids'],['second']);self.assertIsNotNone(out['completeness']['sodium_mg']['known_subtotal'])
 def test_empty_meal_not_zero(self):self.assertIsNone(compute_meal(self.kb,self.request(items=[]))['totals']['energy_kcal'])
 def test_negative_quantity(self):
  r=self.request();r['items'][0]['amount']=-10
  with self.assertRaises(Exception):compute_meal(self.kb,r)
 def test_nan_quantity(self):
  r=self.request();r['items'][0]['amount']=float('nan')
  with self.assertRaises(Exception):compute_meal(self.kb,r)
 def test_unknown_food(self):
  r=self.request();r['items'][0]['food_id']='nonexistent'
  with self.assertRaises(ValueError):compute_meal(self.kb,r)
 def test_duplicate_detection(self):
  r=self.request();r['items'][0]['detection_ids']=['d1'];second=copy.deepcopy(r['items'][0]);second['item_id']='rice2';r['items'].append(second)
  with self.assertRaises(ValueError):compute_meal(self.kb,r)
 def test_component_double_count(self):
  r=self.request();r['items'][0]['parent_item_id']='whole_dish'
  with self.assertRaises(ValueError):compute_meal(self.kb,r)
 def test_no_day_success_from_meal(self):
  n=compute_meal(self.kb,self.request());p=self.profile(clinician_daily_targets=[self.target()]);a=assess_targets(self.kb,n,p)
  self.assertEqual(a['messages'][0]['status'],'day_assessment_unavailable')
 def test_full_day_comparison(self):
  n=compute_meal(self.kb,self.request(period='day',day_log_complete=True));p=self.profile(clinician_daily_targets=[self.target()]);a=assess_targets(self.kb,n,p)
  self.assertEqual(a['messages'][0]['status'],'not_exceeding_recorded_target_for_logged_day')
 def test_model_confirm_click_not_measurement(self):
  r=self.request();r['items'][0]['quantity_source']='model_estimate';n=compute_meal(self.kb,r);self.assertFalse(n['eligible_for_target_comparison'])
  a=assess_targets(self.kb,n,self.profile(clinician_daily_targets=[self.target()]));self.assertEqual(a['messages'][0]['status'],'not_assessed_unconfirmed_context_or_quantity')
 def test_units_not_interchangeable(self):
  with self.assertRaises(ValueError):assess_targets(self.kb,compute_meal(self.kb,self.request()),self.profile(clinician_daily_targets=[self.target(unit='mg/day')]))
 def test_no_automatic_patient_targets(self):self.assertEqual(assess_targets(self.kb,compute_meal(self.kb,self.request()),self.profile())['messages'],[])
 def test_dialysis_excludes_predialysis_protein(self):
  docs=retrieve_clinical(self.kb,'protein đạm',self.profile(conditions=['CKD'],dialysis='hemodialysis'),30)
  self.assertNotIn('CKD_PROTEIN_TARGET',{d['chunk_id'] for d in docs});self.assertIn('CKD_DIALYSIS',{d['chunk_id'] for d in docs})
 def test_children_filtered(self):self.assertEqual(retrieve_clinical(self.kb,'dinh dưỡng',self.profile(age_years=10)),[])
 def test_aki_filtered(self):self.assertEqual(retrieve_clinical(self.kb,'protein',self.profile(conditions=['CKD'],kidney_disease_type='AKI')),[])
 def test_unknown_diabetes_type_filtered(self):self.assertEqual(retrieve_clinical(self.kb,'đường',self.profile(conditions=['T2DM'],diabetes_type=None)),[])
 def test_multimorbidity_retained(self):
  docs=retrieve_clinical(self.kb,'natri',self.profile());present={c for d in docs for c in d['conditions']};self.assertEqual(present,{'CKD','T2DM','CVD'})
 def test_search_without_accents(self):self.assertEqual(search_foods(self.kb,'com trang')[0]['food_id'],'USDA_FDC_168878')
 def test_provenance_hashes(self):
  snapshot_path=HERE/'provenance/selected_nutrition_source_records.json'
  if not snapshot_path.is_file():
   self.skipTest('Local VietFood composition source records are unavailable')
  snapshots=json.loads(snapshot_path.read_text(encoding='utf-8'));hashes={hashlib.sha256(json.dumps(x['record'],ensure_ascii=False,sort_keys=True).encode()).hexdigest() for x in snapshots}
  self.assertEqual(len(hashes),150)
  for f in self.kb['food']['foods']:self.assertIn(f['nutrition']['source_record_sha256'],hashes)
 def test_adapter_no_auto_confirmation(self):
  r={'schema_version':'1.0.0','detections':[{'detection_id':'d1','dataset_class_id':34,'label':'Hamburger','portion':{'estimated_mass_g':861.28}}]}
  d=adapter_candidates(self.kb,r)[0];self.assertFalse(d['food_confirmed']);self.assertFalse(d['quantity_confirmed']);self.assertEqual(d['suggested_mass_g'],861.28)
 def test_rag_no_invented_citations(self):
  payload=prepare_rag(self.kb,self.request(),self.profile(),'natri');self.assertEqual(set(payload['allowed_citation_ids']),{d['chunk_id'] for d in payload['clinical_evidence']})
if __name__=='__main__':unittest.main()
