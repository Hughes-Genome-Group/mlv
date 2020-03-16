CREATE SEQUENCE public.genomes_id_seq
    INCREMENT 1
    START 9
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE SEQUENCE public.user_preferences_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE SEQUENCE public.jobs_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE SEQUENCE public.permissions_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE SEQUENCE public.projects_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE SEQUENCE public.users_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE SEQUENCE public.shared_objects_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;


CREATE TABLE public.users
(
    id integer NOT NULL DEFAULT nextval('users_id_seq'::regclass),
    email character varying(255) COLLATE pg_catalog."default" NOT NULL DEFAULT ''::character varying,
    confirmed_at timestamp without time zone,
    password character varying(255) COLLATE pg_catalog."default" NOT NULL DEFAULT ''::character varying,
    is_active boolean NOT NULL DEFAULT false,
    first_name character varying(50) COLLATE pg_catalog."default" NOT NULL DEFAULT ''::character varying,
    last_name character varying(50) COLLATE pg_catalog."default" NOT NULL DEFAULT ''::character varying,
    administrator boolean DEFAULT false,
    institution text COLLATE pg_catalog."default",
    CONSTRAINT users_pkey PRIMARY KEY (id),
    CONSTRAINT users_email_key UNIQUE (email)
)
WITH (
    OIDS = FALSE
)
TABLESPACE pg_default;


CREATE TABLE public.genomes
(
    id integer NOT NULL DEFAULT nextval('genomes_id_seq'::regclass),
    name character varying(50) COLLATE pg_catalog."default" NOT NULL,
    label text COLLATE pg_catalog."default",
    data jsonb,
    database text COLLATE pg_catalog."default",
    date_added timestamp without time zone DEFAULT now(),
    connections integer,
    icon text COLLATE pg_catalog."default",
    is_public boolean DEFAULT true,
    chrom_sizes json,
    small_icon text COLLATE pg_catalog."default",
    CONSTRAINT genomes_primary_key PRIMARY KEY (id),
    CONSTRAINT name_unique UNIQUE (name)
)
WITH (
    OIDS = FALSE
)
TABLESPACE pg_default;

CREATE TABLE public.jobs
(
    id integer NOT NULL DEFAULT nextval('jobs_id_seq'::regclass),
    inputs json,
    user_id integer,
    outputs json,
    sent_on timestamp without time zone DEFAULT now(),
    status character varying(200) COLLATE pg_catalog."default",
    class_name character varying(200) COLLATE pg_catalog."default",
    genome character varying(100) COLLATE pg_catalog."default",
    finished_on timestamp without time zone,
    is_deleted boolean DEFAULT false,
    type character varying(200) COLLATE pg_catalog."default",
    CONSTRAINT jobs_pkey PRIMARY KEY (id),
    CONSTRAINT jobs_user_id_fkey FOREIGN KEY (user_id)
        REFERENCES public.users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)
WITH (
    OIDS = FALSE
)
TABLESPACE pg_default;

CREATE TABLE public.permissions
(
    id integer NOT NULL DEFAULT nextval('permissions_id_seq'::regclass),
    user_id integer,
    permission character varying(200) COLLATE pg_catalog."default" NOT NULL,
    value character varying(200) COLLATE pg_catalog."default" NOT NULL,
    CONSTRAINT permissions_pkey PRIMARY KEY (id),
    CONSTRAINT permissions_users_user_id FOREIGN KEY (user_id)
        REFERENCES public.users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE
)
WITH (
    OIDS = FALSE
)
TABLESPACE pg_default;


CREATE TABLE public.projects
(
    id integer NOT NULL DEFAULT nextval('projects_id_seq'::regclass),
    name text COLLATE pg_catalog."default",
    date_added timestamp without time zone DEFAULT now(),
    data_modified timestamp without time zone DEFAULT now(),
    owner integer,
    is_deleted boolean DEFAULT false,
    type text COLLATE pg_catalog."default",
    data jsonb,
    is_public boolean DEFAULT false,
    date_made_public timestamp without time zone,
    status text COLLATE pg_catalog."default",
    genome text COLLATE pg_catalog."default",
    parent integer,
    description text COLLATE pg_catalog."default",
    CONSTRAINT projects_pkey PRIMARY KEY (id),
    CONSTRAINT projects_genome_genomes_name FOREIGN KEY (genome)
        REFERENCES public.genomes (name) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT projects_owner_users_user_id FOREIGN KEY (owner)
        REFERENCES public.users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)
WITH (
    OIDS = FALSE
)
TABLESPACE pg_default;


CREATE INDEX fki_projects_genome_genomes_name
    ON public.projects USING btree
    (genome COLLATE pg_catalog."default")
    TABLESPACE pg_default;



CREATE INDEX fki_projects_owner_users_user_id
    ON public.projects USING btree
    (owner)
    TABLESPACE pg_default;

CREATE TABLE public.shared_objects
(
    owner integer,
    shared_with integer,
    object_id integer,
    id integer NOT NULL DEFAULT nextval('shared_objects_id_seq'::regclass),
    date_shared timestamp without time zone DEFAULT now(),
    level text COLLATE pg_catalog."default" DEFAULT 'view'::text,
    CONSTRAINT shared_object_pk PRIMARY KEY (id)
)
WITH (
    OIDS = FALSE
)
TABLESPACE pg_default;

CREATE TABLE public.user_preferences
(
    id integer NOT NULL DEFAULT nextval('user_preferences_id_seq'::regclass),
    preference text COLLATE pg_catalog."default" NOT NULL,
    data json,
    user_id integer,
    CONSTRAINT user_preferences_pkey PRIMARY KEY (id)
)
WITH (
    OIDS = FALSE
)
TABLESPACE pg_default;
