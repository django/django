ALTER TABLE {table_name} ALTER COLUMN now SET DEFAULT CURRENT_TIMESTAMP;

CREATE OR REPLACE FUNCTION set_num()
RETURNS trigger AS '
    BEGIN
        IF NEW.num IS NULL THEN
            NEW.num = 0;
        ELSE
            NEW.num := NEW.num + NEW.num;
        END IF;
        NEW.num_a = 1;
        NEW.num_b = 1;
        return NEW;
    END'
LANGUAGE 'plpgsql';

DROP TRIGGER IF EXISTS auto_set_num ON {table_name};
CREATE TRIGGER auto_set_num
BEFORE UPDATE OR INSERT ON {table_name}
FOR EACH ROW
EXECUTE PROCEDURE set_num();
