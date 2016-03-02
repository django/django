CREATE OR REPLACE TRIGGER auto_set_field_trigger
BEFORE UPDATE OR INSERT ON {table_name}
FOR EACH ROW
    BEGIN
        SELECT systimestamp INTO :new.now FROM DUAL;

        IF :new.num IS NULL THEN
            :new.num := 0;
        ELSE
            :new.num := :new.num + :new.num;
        END IF;

        :new.num_a := 1;
        :new.num_b := 1;
    END;
