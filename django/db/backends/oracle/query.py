def get_query_set_class(DefaultQuerySet):
    """
    Create a custom QuerySet class for Oracle.
    """
    
    class OracleQuerySet(DefaultQuerySet):
        pass
        
    return OracleQuerySet