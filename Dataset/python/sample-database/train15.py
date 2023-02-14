def _infer_schema(row, names=None):
    """Infer the schema from dict/namedtuple/object"""
    if isinstance(row, dict):
        items = sorted(row.items())

    elif isinstance(row, (tuple, list)):
        if hasattr(row, "__fields__"):  # Row
            items = zip(row.__fields__, tuple(row))
        elif hasattr(row, "_fields"):  # namedtuple
            items = zip(row._fields, tuple(row))
        else:
            if names is None:
                names = ['_%d' % i for i in range(1, len(row) + 1)]
            elif len(names) < len(row):
                names.extend('_%d' % i for i in range(len(names) + 1, len(row) + 1))
            items = zip(names, row)

    elif hasattr(row, "__dict__"):  # object
        items = sorted(row.__dict__.items())

    else:
        raise TypeError("Can not infer schema for type: %s" % type(row))

    fields = [StructField(k, _infer_type(v), True) for k, v in items]
    return StructType(fields)