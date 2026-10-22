"""Recover concatenated JSON actions without executing speculative future actions."""
import json


def first_action(content):
    if not isinstance(content,str) or len(content)>24000:
        raise ValueError('Action response exceeds the size limit')
    decoder=json.JSONDecoder(); rest=content.strip(); actions=[]
    while rest:
        item,end=decoder.raw_decode(rest)
        if not isinstance(item,dict) or item.get('action') not in {'plan','hypothesis','tool','finish'}:
            raise ValueError('Each policy item must be a recognized JSON action')
        actions.append(item)
        if len(actions)>32:raise ValueError('Too many concatenated policy actions')
        rest=rest[end:].strip()
    if not actions:raise ValueError('No JSON action')
    # Later actions were produced without observing this action's execution. Discard them.
    return actions[0],len(actions)-1
