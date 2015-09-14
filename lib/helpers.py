def recursive_str_to_unicode(target):
    """
    recursive function for convert all string in dict, tuple and list to unicode
    """
    pack_result = []

    if isinstance(target, dict):
        level = {}
        for key, val in target.items():
            ukey = recursive_str_to_unicode(key)
            uval = recursive_str_to_unicode(val)
            level[ukey] = uval
        pack_result.append(level)
    elif isinstance(target, list):
        level = []
        for leaf in target:
            uleaf = recursive_str_to_unicode(leaf)
            level.append(uleaf)
        pack_result.append(level)
    elif isinstance(target, tuple):
        level = []
        for leaf in target:
            uleaf = recursive_str_to_unicode(leaf)
            level.append(uleaf)
        pack_result.append(tuple(level))
    elif isinstance(target, str):
        return as_unicode(target)
    else:
        return target

    result = pack_result.pop()
    return result


def as_unicode(string):
    return same_string_type_as("", string)


def same_string_type_as(type_source, content_source):
    return content_source