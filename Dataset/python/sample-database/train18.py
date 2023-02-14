def _make_type_verifier(dataType, nullable=True, name=None):
    """
    Make a verifier that checks the type of obj against dataType and raises a TypeError if they do
    not match.

    This verifier also checks the value of obj against datatype and raises a ValueError if it's not
    within the allowed range, e.g. using 128 as ByteType will overflow. Note that, Python float is
    not checked, so it will become infinity when cast to Java float if it overflows.

    >>> _make_type_verifier(StructType([]))(None)
    >>> _make_type_verifier(StringType())("")
    >>> _make_type_verifier(LongType())(0)
    >>> _make_type_verifier(ArrayType(ShortType()))(list(range(3)))
    >>> _make_type_verifier(ArrayType(StringType()))(set()) # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    TypeError:...
    >>> _make_type_verifier(MapType(StringType(), IntegerType()))({})
    >>> _make_type_verifier(StructType([]))(())
    >>> _make_type_verifier(StructType([]))([])
    >>> _make_type_verifier(StructType([]))([1]) # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    ValueError:...
    >>> # Check if numeric values are within the allowed range.
    >>> _make_type_verifier(ByteType())(12)
    >>> _make_type_verifier(ByteType())(1234) # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    ValueError:...
    >>> _make_type_verifier(ByteType(), False)(None) # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    ValueError:...
    >>> _make_type_verifier(
    ...     ArrayType(ShortType(), False))([1, None]) # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    ValueError:...
    >>> _make_type_verifier(MapType(StringType(), IntegerType()))({None: 1})
    Traceback (most recent call last):
        ...
    ValueError:...
    >>> schema = StructType().add("a", IntegerType()).add("b", StringType(), False)
    >>> _make_type_verifier(schema)((1, None)) # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    ValueError:...
    """

    if name is None:
        new_msg = lambda msg: msg
        new_name = lambda n: "field %s" % n
    else:
        new_msg = lambda msg: "%s: %s" % (name, msg)
        new_name = lambda n: "field %s in %s" % (n, name)

    def verify_nullability(obj):
        if obj is None:
            if nullable:
                return True
            else:
                raise ValueError(new_msg("This field is not nullable, but got None"))
        else:
            return False

    _type = type(dataType)

    def assert_acceptable_types(obj):
        assert _type in _acceptable_types, \
            new_msg("unknown datatype: %s for object %r" % (dataType, obj))

    def verify_acceptable_types(obj):
        # subclass of them can not be fromInternal in JVM
        if type(obj) not in _acceptable_types[_type]:
            raise TypeError(new_msg("%s can not accept object %r in type %s"
                                    % (dataType, obj, type(obj))))

    if isinstance(dataType, StringType):
        # StringType can work with any types
        verify_value = lambda _: _

    elif isinstance(dataType, UserDefinedType):
        verifier = _make_type_verifier(dataType.sqlType(), name=name)

        def verify_udf(obj):
            if not (hasattr(obj, '__UDT__') and obj.__UDT__ == dataType):
                raise ValueError(new_msg("%r is not an instance of type %r" % (obj, dataType)))
            verifier(dataType.toInternal(obj))

        verify_value = verify_udf

    elif isinstance(dataType, ByteType):
        def verify_byte(obj):
            assert_acceptable_types(obj)
            verify_acceptable_types(obj)
            if obj < -128 or obj > 127:
                raise ValueError(new_msg("object of ByteType out of range, got: %s" % obj))

        verify_value = verify_byte

    elif isinstance(dataType, ShortType):
        def verify_short(obj):
            assert_acceptable_types(obj)
            verify_acceptable_types(obj)
            if obj < -32768 or obj > 32767:
                raise ValueError(new_msg("object of ShortType out of range, got: %s" % obj))

        verify_value = verify_short

    elif isinstance(dataType, IntegerType):
        def verify_integer(obj):
            assert_acceptable_types(obj)
            verify_acceptable_types(obj)
            if obj < -2147483648 or obj > 2147483647:
                raise ValueError(
                    new_msg("object of IntegerType out of range, got: %s" % obj))

        verify_value = verify_integer

    elif isinstance(dataType, ArrayType):
        element_verifier = _make_type_verifier(
            dataType.elementType, dataType.containsNull, name="element in array %s" % name)

        def verify_array(obj):
            assert_acceptable_types(obj)
            verify_acceptable_types(obj)
            for i in obj:
                element_verifier(i)

        verify_value = verify_array

    elif isinstance(dataType, MapType):
        key_verifier = _make_type_verifier(dataType.keyType, False, name="key of map %s" % name)
        value_verifier = _make_type_verifier(
            dataType.valueType, dataType.valueContainsNull, name="value of map %s" % name)

        def verify_map(obj):
            assert_acceptable_types(obj)
            verify_acceptable_types(obj)
            for k, v in obj.items():
                key_verifier(k)
                value_verifier(v)

        verify_value = verify_map

    elif isinstance(dataType, StructType):
        verifiers = []
        for f in dataType.fields:
            verifier = _make_type_verifier(f.dataType, f.nullable, name=new_name(f.name))
            verifiers.append((f.name, verifier))

        def verify_struct(obj):
            assert_acceptable_types(obj)

            if isinstance(obj, dict):
                for f, verifier in verifiers:
                    verifier(obj.get(f))
            elif isinstance(obj, Row) and getattr(obj, "__from_dict__", False):
                # the order in obj could be different than dataType.fields
                for f, verifier in verifiers:
                    verifier(obj[f])
            elif isinstance(obj, (tuple, list)):
                if len(obj) != len(verifiers):
                    raise ValueError(
                        new_msg("Length of object (%d) does not match with "
                                "length of fields (%d)" % (len(obj), len(verifiers))))
                for v, (_, verifier) in zip(obj, verifiers):
                    verifier(v)
            elif hasattr(obj, "__dict__"):
                d = obj.__dict__
                for f, verifier in verifiers:
                    verifier(d.get(f))
            else:
                raise TypeError(new_msg("StructType can not accept object %r in type %s"
                                        % (obj, type(obj))))
        verify_value = verify_struct

    else:
        def verify_default(obj):
            assert_acceptable_types(obj)
            verify_acceptable_types(obj)

        verify_value = verify_default

    def verify(obj):
        if not verify_nullability(obj):
            verify_value(obj)

    return verify