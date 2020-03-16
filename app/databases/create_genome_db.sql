CREATE SEQUENCE public.view_sets_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 2147483647
    CACHE 1;

    
CREATE SEQUENCE public.gene_sets_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 2147483647
    CACHE 1;
 

CREATE TABLE public.view_sets
(
    id integer NOT NULL DEFAULT nextval('view_sets_id_seq'::regclass),
    table_name character varying(100) COLLATE pg_catalog."default",
    name character varying(200) COLLATE pg_catalog."default",
    description text,
    date_added timestamp without time zone default now(),
    date_modified timestamp without time zone default now(),
    owner integer default 0,
    is_public boolean default FALSE,
    fields json,
    data json,
    date_made_public timestamp without time zone,
    status text,
    is_deleted boolean default FALSE,
    CONSTRAINT view_sets_pkey PRIMARY KEY (id)
   
)
WITH (
    OIDS = FALSE
)
TABLESPACE pg_default;



CREATE TABLE public.gene_sets
(
    id integer NOT NULL DEFAULT nextval('gene_sets_id_seq'::regclass),
    name character varying(100) COLLATE pg_catalog."default" NOT NULL,
    table_name character varying(150) COLLATE pg_catalog."default",
    data jsonb,
    date_added timestamp without time zone default now(),
    date_modified timestamp without time zone default now(),
    is_deleted boolean default FALSE,
    description text,
    CONSTRAINT gene_sets_pkey PRIMARY KEY (id)
)
WITH (
    OIDS = FALSE
)
TABLESPACE pg_default;


    


    
    
    
    
