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
    CONSTRAINT {table_name}_pkey PRIMARY KEY (id),
    field_id integer,
    exp_id integer,
    type character varying(20),
    {extra_columns}
)
WITH (
    OIDS = FALSE
)
TABLESPACE pg_default;

ALTER TABLE public.{table_name}
    OWNER to {db_user};