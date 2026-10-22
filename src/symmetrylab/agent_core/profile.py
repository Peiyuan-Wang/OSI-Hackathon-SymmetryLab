"""Validated user research context. Existing CLI tasks retain their legacy behavior."""

def research_profile(value=None):
    if value is None:
        return {'track':'legacy','material':'','conditions':'','instruments':'','keywords':'','papers':'','taste_notes':'','reuse_lessons':False}
    if not isinstance(value,dict):
        raise ValueError('Research profile must be an object')
    defaults={'track':'theory','material':'','conditions':'','instruments':'','keywords':'','papers':'','taste_notes':'','reuse_lessons':True}
    if set(value)-set(defaults):
        raise ValueError('Unsupported research profile field')
    result=dict(defaults,**value)
    if result['track'] not in {'theory','experiment'}:
        raise ValueError('Choose theory or experiment')
    for key in ('material','conditions','instruments','keywords','papers','taste_notes'):
        if not isinstance(result[key],str) or len(result[key])>(8000 if key=='papers' else 1500):
            raise ValueError('Research context exceeds the allowed length')
    if result['track']=='experiment' and not result['material'].strip():
        raise ValueError('Enter a material for experimental research')
    if type(result['reuse_lessons']) is not bool:
        raise ValueError('Lesson reuse must be boolean')
    return result
