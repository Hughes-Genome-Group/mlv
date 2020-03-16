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
    chromosome character varying(50)  COLLATE pg_catalog."default",
    start integer,
    finish integer,
    track_id integer,
    {extra_columns}
    CONSTRAINT {table_name}_pkey PRIMARY KEY (id)
)
WITH (
    OIDS = FALSE
)
TABLESPACE pg_default;

ALTER TABLE public.{table_name}
    OWNER to {db_user};