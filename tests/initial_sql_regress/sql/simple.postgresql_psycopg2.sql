CREATE OR REPLACE FUNCTION test(val integer) RETURNS integer AS $$
  /* check that an embedded ';' does not raise any issue */
  BEGIN
  RETURN val + 1;
  END; $$
LANGUAGE PLPGSQL;
