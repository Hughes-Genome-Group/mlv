CREATE SEQUENCE public.{table_name}_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 2147483647
    CACHE 1;

ALTER SEQUENCE public.{table_name}_id_seq
    OWNER TO {db_user};


CREATE TABLE public.{table_name}
(
    id integer NOT NULL DEFAULT nextval('{table_name}_id_seq'::regclass),
    name character varying(255) COLLATE pg_catalog."default",
    chrom character varying(50) COLLATE pg_catalog."default",
    strand character varying(1) COLLATE pg_catalog."default",
    tx_start integer,
    tx_end integer,
    cd_start integer,
    cd_end integer,
    exon_count integer,
    exon_starts json,
    exon_ends json,
    score integer,
    cds_start_stat character varying(10) COLLATE pg_catalog."default",
    cds_end_stat character varying(10) COLLATE pg_catalog."default",
    name2 character varying(255) COLLATE pg_catalog."default",
    exon_frames json,
    CONSTRAINT {table_name}_pkey PRIMARY KEY (id)
)
WITH (
    OIDS = FALSE
)
TABLESPACE pg_default;

ALTER TABLE public.{table_name}
    OWNER to {db_user};