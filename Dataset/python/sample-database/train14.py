def _infer_type(obj):
    """Infer the DataType from obj
    """
    if obj is None:
        return NullType()

    if hasattr(obj, '__UDT__'):
        return obj.__UDT__

    dataType = _type_mappings.get(type(obj))
    if dataType is DecimalType:
        # the precision and scale of `obj` may be different from row to row.
        return DecimalType(38, 18)
    elif dataType is not None:
        return dataType()

    if isinstance(obj, dict):
        for key, value in obj.items():
            if key is not None and value is not None:
                return MapType(_infer_type(key), _infer_type(value), True)
        return MapType(NullType(), NullType(), True)
    elif isinstance(obj, list):
        for v in obj:
            if v is not None:
                return ArrayType(_infer_type(obj[0]), True)
        return ArrayType(NullType(), True)
    elif isinstance(obj, array):
        if obj.typecode in _array_type_mappings:
            return ArrayType(_array_type_mappings[obj.typecode](), False)
        else:
            raise TypeError("not supported type: array(%s)" % obj.typecode)
    else:
        try:
            return _infer_schema(obj)
        except TypeError:
            raise TypeError("not supported type: %s" % type(obj))