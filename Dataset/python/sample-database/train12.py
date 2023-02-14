def _parse_datatype_string(s):
    """
    Parses the given data type string to a :class:`DataType`. The data type string format equals
    to :class:`DataType.simpleString`, except that top level struct type can omit
    the ``struct<>`` and atomic types use ``typeName()`` as their format, e.g. use ``byte`` instead
    of ``tinyint`` for :class:`ByteType`. We can also use ``int`` as a short name
    for :class:`IntegerType`. Since Spark 2.3, this also supports a schema in a DDL-formatted
    string and case-insensitive strings.

    >>> _parse_datatype_string("int ")
    IntegerType
    >>> _parse_datatype_string("INT ")
    IntegerType
    >>> _parse_datatype_string("a: byte, b: decimal(  16 , 8   ) ")
    StructType(List(StructField(a,ByteType,true),StructField(b,DecimalType(16,8),true)))
    >>> _parse_datatype_string("a DOUBLE, b STRING")
    StructType(List(StructField(a,DoubleType,true),StructField(b,StringType,true)))
    >>> _parse_datatype_string("a: array< short>")
    StructType(List(StructField(a,ArrayType(ShortType,true),true)))
    >>> _parse_datatype_string(" map<string , string > ")
    MapType(StringType,StringType,true)

    >>> # Error cases
    >>> _parse_datatype_string("blabla") # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    ParseException:...
    >>> _parse_datatype_string("a: int,") # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    ParseException:...
    >>> _parse_datatype_string("array<int") # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    ParseException:...
    >>> _parse_datatype_string("map<int, boolean>>") # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    ParseException:...
    """
    sc = SparkContext._active_spark_context

    def from_ddl_schema(type_str):
        return _parse_datatype_json_string(
            sc._jvm.org.apache.spark.sql.types.StructType.fromDDL(type_str).json())

    def from_ddl_datatype(type_str):
        return _parse_datatype_json_string(
            sc._jvm.org.apache.spark.sql.api.python.PythonSQLUtils.parseDataType(type_str).json())

    try:
        # DDL format, "fieldname datatype, fieldname datatype".
        return from_ddl_schema(s)
    except Exception as e:
        try:
            # For backwards compatibility, "integer", "struct<fieldname: datatype>" and etc.
            return from_ddl_datatype(s)
        except:
            try:
                # For backwards compatibility, "fieldname: datatype, fieldname: datatype" case.
                return from_ddl_datatype("struct<%s>" % s.strip())
            except:
                raise e