CREATE INDEX {table_name}_chromosome_start_finish_idx
    ON public.{table_name} USING btree
    (chromosome COLLATE pg_catalog."default", start, finish)
    TABLESPACE pg_default;