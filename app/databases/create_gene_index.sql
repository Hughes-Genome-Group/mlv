CREATE INDEX {table_name}_chrom_tsstart_tsfinish_idx
    ON public.{table_name} USING btree
    (chrom COLLATE pg_catalog."default", tx_start, tx_end)
    TABLESPACE pg_default;
CREATE INDEX {table_name}_chrom_cdstart_cdfinish_idx
    ON public.{table_name} USING btree
    (chrom COLLATE pg_catalog."default", cd_start, cd_end)
    TABLESPACE pg_default;