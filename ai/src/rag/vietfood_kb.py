"""Nutrition arithmetic and source-grounded RAG preparation; no LLM arithmetic."""
from pathlib import Path
import json,math,re,unicodedata,difflib,argparse
HERE=Path(__file__).resolve().parents[3]/'data/knowledge_base/vietfood'

def norm(text):
    text=unicodedata.normalize('NFKD',str(text).lower().replace('đ','d')).encode('ascii','ignore').decode()
    return ' '.join(re.sub('[^a-z0-9 ]',' ',text).split())

def load_kb(folder=HERE):
    root=Path(folder)
    kb={name:json.loads((root/'data'/filename).read_text(encoding='utf-8')) for name,filename in [('food','food_kb.json'),('clinical','clinical_kb.json'),('sources','sources.json'),('mapping','model_mapping.json')]}
    kb['schema']=json.loads((root/'schemas/kb_schema.json').read_text(encoding='utf-8'))
    return kb

def validate_document(kb,document,definition):
    from jsonschema import Draft202012Validator
    json.dumps(document,allow_nan=False)
    Draft202012Validator({'$ref':'#/$defs/'+definition,'$defs':kb['schema']['$defs']}).validate(document)

def validate(kb):
    for name,definition in [('food','FoodKB'),('clinical','ClinicalKB'),('sources','Sources'),('mapping','ModelMapping')]:
        validate_document(kb,kb[name],definition)
    foods=kb['food']['foods']; fids=[f['food_id'] for f in foods]
    assert len(fids)==len(set(fids)), 'Duplicate food ID'
    source_list=kb['sources']['sources']; sids={s['source_id'] for s in source_list}
    assert len(sids)==len(source_list), 'Duplicate source ID'
    chunks=kb['clinical']['chunks']; cids={c['chunk_id'] for c in chunks}
    assert len(cids)==len(chunks),'Duplicate clinical chunk ID'
    for f in foods:
        assert f['nutrition']['source_id'] in sids
        assert f['reference_serving']['source_id'] in sids
    for c in chunks: assert c['source_id'] in sids
    for t in kb['clinical']['reference_thresholds']: assert t['basis_chunk_id'] in cids
    entries=kb['mapping']['entries']
    assert sorted(e['dataset_class_id'] for e in entries)==list(range(68))
    assert {e['dataset_class_id'] for e in entries if e['supported_output']}==set(range(68))-{20,27,29,30,32,42,49,50,52,55,56}
    for e in entries:
        assert set(e['candidate_food_ids'])<=set(fids)
        assert not e['automatic_mapping']
    return {'valid':True,'foods':len(foods),'clinical_chunks':len(chunks),'supported_model_classes':57}

def search_foods(kb,query,limit=8):
    q=norm(query)
    if not q:return []
    scored=[]
    for f in kb['food']['foods']:
        candidates=[norm(f['name_vi'])]+[norm(a) for a in f['aliases']]
        score=max(1.0 if q==n else .85 if q in n else difflib.SequenceMatcher(None,q,n).ratio()*.7 for n in candidates)
        if score>=.35:
            scored.append({'food_id':f['food_id'],'name_vi':f['name_vi'],'food_state':f['food_state'],'reference_serving':f['reference_serving'],'match_score':round(score,4),'selection_required':True})
    return sorted(scored,key=lambda x:(-x['match_score'],x['food_id']))[:limit]

def adapter_candidates(kb,response):
    """Read adapter v1; never treat a candidate ID or model grams as confirmed."""
    if response.get('schema_version')!='1.0.0':raise ValueError('Unsupported adapter response version')
    mapping={m['dataset_class_id']:m for m in kb['mapping']['entries']}
    result=[]
    for d in response.get('detections',[]):
        entry=mapping.get(d['dataset_class_id'])
        if not entry or not entry['supported_output']:continue
        if entry['model_label']!=d['label']:raise ValueError('Model label/ID mismatch')
        result.append({'detection_id':d['detection_id'],'model_label':d['label'],'candidate_food_ids':entry['candidate_food_ids'],
                       'suggested_mass_g':d.get('portion',{}).get('estimated_mass_g'),
                       'quantity_source':'model_estimate','food_confirmed':False,'quantity_confirmed':False,
                       'status':entry['status']})
    return result

def compute_meal(kb,request):
    validate_document(kb,request,'MealRequest')
    foods={f['food_id']:f for f in kb['food']['foods']}
    nutrients=list(kb['food']['nutrient_units']);items=[];warnings=[];seen=set();detection_ids=set()
    for item in request['items']:
        if item['item_id'] in seen:raise ValueError('Duplicate item_id')
        seen.add(item['item_id'])
        f=foods.get(item['food_id'])
        if f is None:raise ValueError('Unknown food_id: '+item['food_id'])
        if item.get('parent_item_id') is not None:raise ValueError('Do not count a whole dish and its component as separate items; resolve first')
        refs=item.get('detection_ids',[])
        if len(refs)!=len(set(refs)) or detection_ids.intersection(refs):raise ValueError('Detection counted more than once')
        detection_ids.update(refs)
        if item['unit']=='reference_serving' and item['quantity_source'] in {'weighed','model_estimate'}:
            raise ValueError('Weighed/model quantities must use grams')
        grams=item['amount'] if item['unit']=='g' else item['amount']*f['reference_serving']['grams']
        if not math.isfinite(grams) or grams<=0:raise ValueError('Invalid gram quantity')
        values={k:None if f['nutrition']['values'][k] is None else f['nutrition']['values'][k]*grams/100 for k in nutrients}
        if not item['food_confirmed']: warnings.append('FOOD_VARIANT_UNCONFIRMED')
        if not item['quantity_confirmed']:warnings.append('QUANTITY_UNCONFIRMED')
        if item['quantity_source']=='model_estimate':warnings.append('MODEL_MASS_UNVALIDATED')
        if item['unit']=='reference_serving' or item['quantity_source']=='reference_default':warnings.append('REFERENCE_PORTION_NOT_PERSONAL_TARGET')
        items.append({'item_id':item['item_id'],'food_id':f['food_id'],'name_vi':f['name_vi'],'grams':grams,'quantity_source':item['quantity_source'],
                      'food_confirmed':item['food_confirmed'],'quantity_confirmed':item['quantity_confirmed'],
                      'nutrients':values,'source_id':f['nutrition']['source_id'],'record_id':f['nutrition']['record_id'],
                      'source_record_sha256':f['nutrition']['source_record_sha256']})
    if not request['overlap_reviewed']:warnings.append('OVERLAPPING_DISH_COMPONENTS_NOT_REVIEWED')
    totals={};completeness={}
    for n in nutrients:
        known=[i['nutrients'][n] for i in items if i['nutrients'][n] is not None]
        missing=[i['item_id'] for i in items if i['nutrients'][n] is None]
        totals[n]=sum(known) if items and not missing else None
        completeness[n]={'known_items':len(known),'total_items':len(items),'missing_item_ids':missing,
                         'known_subtotal':sum(known) if known else None,'unit':kb['food']['nutrient_units'][n]}
    if any(v is None for v in totals.values()):warnings.append('INCOMPLETE_NUTRIENT_DATA')
    confirmed=bool(items) and request['overlap_reviewed'] and all(i['food_confirmed'] and i['quantity_confirmed'] for i in items)
    # Clicking confirm does not turn an image model estimate into a measured quantity.
    eligible=confirmed and all(i['quantity_source']!='model_estimate' for i in items)
    result={'request_id':request['request_id'],'kb_version':'2.0.0','period':request['period'],'day_log_complete':request['day_log_complete'],
            'items':items,'totals':totals,'completeness':completeness,'inputs_confirmed':confirmed,
            'eligible_for_target_comparison':eligible,'calculation_status':'empty' if not items else 'estimated_from_composition_table',
            'warnings':sorted(set(warnings))}
    json.dumps(result,allow_nan=False)
    return result

def assess_targets(kb,nutrition,profile):
    validate_document(kb,profile,'Profile')
    context_needed=[];messages=[];warnings=[]
    adult=profile['age_years'] is not None and profile['age_years']>=18
    if not adult:context_needed.append('adult_age_confirmation')
    if profile.get('pregnant') is not False:context_needed.append('pregnancy_status_or_specialist_review')
    conds=set(profile['conditions'])
    if 'CKD' in conds:
        for key in ['kidney_disease_type','ckd_stage','dialysis']:
            if profile.get(key) in (None,'unknown'):context_needed.append(key)
        if profile.get('kidney_disease_type')=='AKI' or profile.get('transplant') is True:warnings.append('KIDNEY_SUBGROUP_OUTSIDE_SCOPE')
        if not profile.get('recent_labs'):context_needed.append('recent_kidney_labs_for_individual_advice')
    if 'T2DM' in conds and profile.get('diabetes_type')!='type2':context_needed.append('type2_diabetes_confirmation')
    if 'CVD' in conds and (profile.get('heart_failure') is True or profile.get('fluid_restriction') is True):warnings.append('HEART_FAILURE_REQUIRES_INDIVIDUAL_PLAN')
    if len(conds)>1:warnings.append('COMORBIDITY_DO_NOT_AUTOMERGE_TARGETS')
    if not nutrition['eligible_for_target_comparison']:warnings.append('ONLY_DRAFT_NUTRITION_NO_PERSONAL_TARGET_VERDICT')
    for target in profile['clinician_daily_targets']:
        nutrient=target['nutrient'];expected=kb['food']['nutrient_units'][nutrient]+'/day'
        if target['unit']!=expected:raise ValueError('Daily target unit mismatch: '+nutrient)
        if not target['confirmed'] or not adult or profile.get('pregnant') is not False or not nutrition['eligible_for_target_comparison']:
            status='not_assessed_unconfirmed_context_or_quantity'
        elif nutrition['totals'][nutrient] is None:status='insufficient_nutrient_data'
        else:
            value=nutrition['totals'][nutrient];limit=target['value'];operator=target['operator']
            if operator in ['<','<=']:
                exceeded=value>=limit if operator=='<' else value>limit
                status='estimated_exceeds_reported_daily_target' if exceeded else ('not_exceeding_recorded_target_for_logged_day' if nutrition['period']=='day' and nutrition['day_log_complete'] else 'day_assessment_unavailable')
            else:
                status=('estimated_below_reported_daily_minimum' if value<limit else 'recorded_daily_minimum_reached') if nutrition['period']=='day' and nutrition['day_log_complete'] else 'day_assessment_unavailable'
        messages.append({'nutrient':nutrient,'status':status,'observed_estimate':nutrition['totals'][nutrient],'reported_target':target,
                         'interpretation':'comparison_with_user_reported_plan_not_medical_verdict'})
    return {'messages':messages,'missing_context':sorted(set(context_needed)),'warnings':sorted(set(warnings)),
            'medical_verdict':None,'guideline_thresholds_auto_applied':False}

def applicability(chunk,profile):
    applies=chunk['applies_to']
    if chunk['source_id']=='SYSTEM_V2':return 'applicable'
    age=profile.get('age_years')
    if age is None:return 'needs_context'
    if profile.get('pregnant') is None:return 'needs_context'
    if age<18 or profile.get('pregnant') is True:return 'outside_scope'
    if 'CKD' in chunk['conditions'] and (profile.get('kidney_disease_type')=='AKI' or profile.get('transplant') is True):return 'outside_scope'
    if 'T2DM' in chunk['conditions']:
        if profile.get('diabetes_type') in (None,'unknown'):return 'needs_context'
        if profile.get('diabetes_type')!='type2':return 'outside_scope'
    needs=False
    for key in applies.get('exclude',[]):
        if key=='acute_kidney_injury':
            if profile.get('kidney_disease_type')=='AKI':return 'outside_scope'
            if profile.get('kidney_disease_type') in (None,'unknown'):needs=True
        elif profile.get(key) is True:return 'outside_scope'
        elif profile.get(key) is None:needs=True
    if 'dialysis' in applies:
        expected=applies['dialysis']; expected=expected if isinstance(expected,list) else [expected]
        if profile.get('dialysis') in (None,'unknown'):needs=True
        elif profile['dialysis'] not in expected:return 'outside_scope'
    if 'ckd_stages' in applies:
        if profile.get('ckd_stage') in (None,'unknown'):needs=True
        elif profile['ckd_stage'] not in applies['ckd_stages']:return 'outside_scope'
    for key in ['progression_risk','sglt2_inhibitor']:
        if key in applies:
            if profile.get(key) is None:needs=True
            elif profile[key]!=applies[key]:return 'outside_scope'
    return 'needs_context' if needs else 'applicable'

def retrieve_clinical(kb,query,profile,limit=6):
    validate_document(kb,profile,'Profile')
    wanted=set(profile['conditions']);tokens=set(norm(query).split());results=[]
    sources={s['source_id']:s for s in kb['sources']['sources']}
    for c in kb['clinical']['chunks']:
        if not wanted.intersection(c['conditions']) or c['source_id']=='SYSTEM_V2':continue
        app=applicability(c,profile)
        if app!='applicable':continue
        texttokens=set(norm(c['text_vi']+' '+c['topic']+' '+' '.join(c['nutrients'])).split())
        score=len(tokens&texttokens)/max(1,len(tokens))
        # Presence of a condition determines scope; lexical score ranks within it.
        results.append({'chunk_id':c['chunk_id'],'text_vi':c['text_vi'],'source_id':c['source_id'],
                        'source_url':sources[c['source_id']]['url'],'locator':c['locator'],
                        'conditions':c['conditions'],'review_status':c['review_status'],'applicability':app,'retrieval_score':round(score,4)})
    ranked=sorted(results,key=lambda r:(-r['retrieval_score'],r['chunk_id']))
    selected=[]
    # Ensure multimorbidity does not silently disappear from the retrieved context.
    for condition in sorted(wanted):
        best=next((r for r in ranked if condition in r['conditions']),None)
        if best and best not in selected:selected.append(best)
    for r in ranked:
        if r not in selected:selected.append(r)
    return selected[:max(limit,len(wanted))]

def prepare_rag(kb,request,profile,query):
    nutrition=compute_meal(kb,request);assessment=assess_targets(kb,nutrition,profile)
    docs=retrieve_clinical(kb,query,profile)
    thresholds=[t for t in kb['clinical']['reference_thresholds'] if t['basis_chunk_id'] in {d['chunk_id'] for d in docs}]
    return {'query':query,'nutrition':nutrition,'assessment':assessment,'clinical_evidence':docs,
            'reference_thresholds_not_patient_targets':thresholds,
            'allowed_citation_ids':[d['chunk_id'] for d in docs],
            'response_requirements':{'cite_each_clinical_claim':True,'calculate_new_nutrients':False,'infer_disease_from_image':False,
                                     'prescribe_or_adjust_medication':False,'claim_safe_or_suitable':False,
                                     'mention_missing_data_and_portion_uncertainty':True},
            'clinical_review_status':'not_clinically_reviewed'}

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['validate','status','search','demo']);p.add_argument('query',nargs='?',default='phở');args=p.parse_args();kb=load_kb()
    if args.command=='validate':result=validate(kb)
    elif args.command=='status':result=json.loads((HERE/'reports/coverage_report.json').read_text(encoding='utf-8'))
    elif args.command=='search':result=search_foods(kb,args.query)
    else:
        request=json.loads((HERE/'examples/meal_request.json').read_text(encoding='utf-8'));profile=json.loads((HERE/'examples/user_profile.json').read_text(encoding='utf-8'))
        result=prepare_rag(kb,request,profile,'Bữa ăn này cần lưu ý carbohydrate, natri và bệnh thận như thế nào?')
    print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
if __name__=='__main__':main()
