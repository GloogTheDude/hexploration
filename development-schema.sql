--
-- PostgreSQL database dump
--

\restrict chMIhVeTmL4RsKuCDq0qvM9a75pdecwjihgYZnpFEUot8QQVABjEqJbzTefJrVz

-- Dumped from database version 18.4 (Debian 18.4-1.pgdg13+1)
-- Dumped by pg_dump version 18.4 (Debian 18.4-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: campaign_role; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.campaign_role AS ENUM (
    'PLAYER',
    'DM'
);


--
-- Name: character_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.character_status AS ENUM (
    'ACTIVE',
    'RETIRED',
    'DEAD'
);


--
-- Name: expedition_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.expedition_status AS ENUM (
    'PLANNING',
    'ACTIVE',
    'DEBRIEFING',
    'RETURNED',
    'LOST',
    'DEAD',
    'ARCHIVED'
);


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: campaign_invitations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.campaign_invitations (
    id integer NOT NULL,
    campaign_id integer NOT NULL,
    invited_user_id integer NOT NULL,
    invited_by_user_id integer NOT NULL,
    status character varying(20) DEFAULT 'PENDING'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    responded_at timestamp with time zone
);


--
-- Name: campaign_invitations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.campaign_invitations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: campaign_invitations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.campaign_invitations_id_seq OWNED BY public.campaign_invitations.id;


--
-- Name: campaign_memberships; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.campaign_memberships (
    id integer NOT NULL,
    campaign_id integer NOT NULL,
    user_id integer NOT NULL,
    role public.campaign_role NOT NULL,
    joined_at timestamp with time zone NOT NULL
);


--
-- Name: campaign_memberships_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.campaign_memberships_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: campaign_memberships_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.campaign_memberships_id_seq OWNED BY public.campaign_memberships.id;


--
-- Name: campaigns; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.campaigns (
    id integer NOT NULL,
    name character varying(160) NOT NULL,
    description text,
    epoch_name character varying(80) NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: campaigns_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.campaigns_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: campaigns_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.campaigns_id_seq OWNED BY public.campaigns.id;


--
-- Name: character_knowledge_observations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.character_knowledge_observations (
    id integer NOT NULL,
    character_id integer NOT NULL,
    expedition_id integer,
    target_type character varying(80) NOT NULL,
    target_id integer NOT NULL,
    observed_game_minute bigint NOT NULL,
    source_type character varying(80) NOT NULL,
    knowledge json NOT NULL,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_character_knowledge_observed_minute_positive CHECK ((observed_game_minute >= 0))
);


--
-- Name: character_knowledge_observations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.character_knowledge_observations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: character_knowledge_observations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.character_knowledge_observations_id_seq OWNED BY public.character_knowledge_observations.id;


--
-- Name: character_map_hex_observations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.character_map_hex_observations (
    id integer NOT NULL,
    character_id integer NOT NULL,
    expedition_id integer,
    map_id integer NOT NULL,
    map_version_id integer NOT NULL,
    q integer NOT NULL,
    r integer NOT NULL,
    observed_game_minute bigint NOT NULL,
    discovery_state character varying(20) NOT NULL,
    terrain_key character varying(80) NOT NULL,
    elevation integer NOT NULL,
    visibility_score integer NOT NULL,
    extra_data json NOT NULL,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_character_map_hex_observed_minute_positive CHECK ((observed_game_minute >= 0))
);


--
-- Name: character_map_hex_observations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.character_map_hex_observations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: character_map_hex_observations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.character_map_hex_observations_id_seq OWNED BY public.character_map_hex_observations.id;


--
-- Name: character_sheet_data_versions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.character_sheet_data_versions (
    id integer NOT NULL,
    character_id integer NOT NULL,
    version integer NOT NULL,
    data json NOT NULL,
    campaign_game_minute bigint DEFAULT '0'::bigint NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_current boolean DEFAULT true NOT NULL
);


--
-- Name: character_sheet_data_versions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.character_sheet_data_versions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: character_sheet_data_versions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.character_sheet_data_versions_id_seq OWNED BY public.character_sheet_data_versions.id;


--
-- Name: character_sheet_versions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.character_sheet_versions (
    id integer NOT NULL,
    character_id integer NOT NULL,
    version integer NOT NULL,
    storage_key character varying(500) NOT NULL,
    original_filename character varying(255) NOT NULL,
    mime_type character varying(100) NOT NULL,
    checksum_sha256 character varying(64),
    campaign_game_minute bigint,
    expedition_id integer,
    created_at timestamp with time zone NOT NULL,
    is_current boolean NOT NULL
);


--
-- Name: character_sheet_versions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.character_sheet_versions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: character_sheet_versions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.character_sheet_versions_id_seq OWNED BY public.character_sheet_versions.id;


--
-- Name: characters; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.characters (
    id integer NOT NULL,
    campaign_id integer NOT NULL,
    owner_user_id integer NOT NULL,
    name character varying(120) NOT NULL,
    race character varying(120),
    character_class character varying(120),
    level integer,
    description text,
    status public.character_status NOT NULL,
    current_game_minute bigint NOT NULL,
    CONSTRAINT ck_character_game_time_positive CHECK ((current_game_minute >= 0))
);


--
-- Name: characters_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.characters_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: characters_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.characters_id_seq OWNED BY public.characters.id;


--
-- Name: debrief_answers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.debrief_answers (
    id integer NOT NULL,
    expedition_id integer NOT NULL,
    question_id integer NOT NULL,
    character_id integer NOT NULL,
    answer text NOT NULL,
    submitted_at timestamp with time zone NOT NULL
);


--
-- Name: debrief_answers_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.debrief_answers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: debrief_answers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.debrief_answers_id_seq OWNED BY public.debrief_answers.id;


--
-- Name: debrief_questions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.debrief_questions (
    id integer NOT NULL,
    template_id integer NOT NULL,
    "position" integer NOT NULL,
    prompt text NOT NULL
);


--
-- Name: debrief_questions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.debrief_questions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: debrief_questions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.debrief_questions_id_seq OWNED BY public.debrief_questions.id;


--
-- Name: debrief_templates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.debrief_templates (
    id integer NOT NULL,
    campaign_id integer NOT NULL,
    name character varying(160) NOT NULL,
    is_active boolean NOT NULL
);


--
-- Name: debrief_templates_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.debrief_templates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: debrief_templates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.debrief_templates_id_seq OWNED BY public.debrief_templates.id;


--
-- Name: expedition_characters; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.expedition_characters (
    id integer NOT NULL,
    expedition_id integer NOT NULL,
    character_id integer NOT NULL,
    joined_game_minute bigint NOT NULL,
    left_game_minute bigint
);


--
-- Name: expedition_characters_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.expedition_characters_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: expedition_characters_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.expedition_characters_id_seq OWNED BY public.expedition_characters.id;


--
-- Name: expedition_reports; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.expedition_reports (
    id integer NOT NULL,
    expedition_id integer NOT NULL,
    published_game_minute bigint NOT NULL,
    title character varying(200) NOT NULL,
    content text NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: expedition_reports_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.expedition_reports_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: expedition_reports_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.expedition_reports_id_seq OWNED BY public.expedition_reports.id;


--
-- Name: expeditions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.expeditions (
    id integer NOT NULL,
    campaign_id integer NOT NULL,
    name character varying(160) NOT NULL,
    status public.expedition_status NOT NULL,
    start_game_minute bigint NOT NULL,
    current_game_minute bigint NOT NULL,
    return_game_minute bigint,
    current_map_version_id integer,
    current_q integer,
    current_r integer,
    created_at timestamp with time zone NOT NULL,
    weather_key character varying(80),
    transport_key character varying(80),
    ping_q integer,
    ping_r integer,
    ping_game_minute bigint,
    ping_user_id integer,
    ping_created_at timestamp with time zone,
    dm_ping_q integer,
    dm_ping_r integer,
    dm_ping_game_minute bigint,
    dm_ping_user_id integer,
    dm_ping_created_at timestamp with time zone,
    CONSTRAINT ck_expedition_current_after_start CHECK ((current_game_minute >= start_game_minute)),
    CONSTRAINT ck_expedition_start_positive CHECK ((start_game_minute >= 0))
);


--
-- Name: expeditions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.expeditions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: expeditions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.expeditions_id_seq OWNED BY public.expeditions.id;


--
-- Name: knowledge_recalls; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.knowledge_recalls (
    id integer NOT NULL,
    expedition_id integer NOT NULL,
    character_id integer NOT NULL,
    page_id integer NOT NULL,
    knowledge_cutoff_game_minute bigint NOT NULL,
    recalled_at_game_minute bigint NOT NULL
);


--
-- Name: knowledge_recalls_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.knowledge_recalls_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: knowledge_recalls_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.knowledge_recalls_id_seq OWNED BY public.knowledge_recalls.id;


--
-- Name: map_areas; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.map_areas (
    id integer NOT NULL,
    map_version_id integer NOT NULL,
    feature_type character varying(80) NOT NULL,
    feature_id integer NOT NULL,
    name character varying(160),
    cells json NOT NULL,
    extra_data json NOT NULL,
    CONSTRAINT ck_map_area_feature_id_positive CHECK ((feature_id > 0))
);


--
-- Name: map_areas_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.map_areas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: map_areas_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.map_areas_id_seq OWNED BY public.map_areas.id;


--
-- Name: map_edges; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.map_edges (
    id integer NOT NULL,
    map_version_id integer NOT NULL,
    from_q integer NOT NULL,
    from_r integer NOT NULL,
    to_q integer NOT NULL,
    to_r integer NOT NULL,
    feature_type character varying(80) NOT NULL,
    feature_id integer NOT NULL,
    name character varying(160),
    extra_data json NOT NULL,
    segment_index integer DEFAULT 0 NOT NULL,
    CONSTRAINT ck_map_edge_feature_id_positive CHECK ((feature_id > 0))
);


--
-- Name: map_edges_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.map_edges_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: map_edges_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.map_edges_id_seq OWNED BY public.map_edges.id;


--
-- Name: map_features; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.map_features (
    id integer NOT NULL,
    campaign_id integer NOT NULL,
    map_id integer NOT NULL,
    feature_type character varying(80) NOT NULL,
    feature_id integer NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    downstream_feature_type character varying(80),
    downstream_feature_id integer
);


--
-- Name: map_features_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.map_features_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: map_features_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.map_features_id_seq OWNED BY public.map_features.id;


--
-- Name: map_hexes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.map_hexes (
    id integer NOT NULL,
    map_version_id integer NOT NULL,
    q integer NOT NULL,
    r integer NOT NULL,
    terrain_key character varying(80) NOT NULL,
    elevation integer NOT NULL,
    travel_cost double precision NOT NULL,
    extra_data json NOT NULL,
    visibility_score integer DEFAULT 3 NOT NULL
);


--
-- Name: map_hexes_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.map_hexes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: map_hexes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.map_hexes_id_seq OWNED BY public.map_hexes.id;


--
-- Name: map_versions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.map_versions (
    id integer NOT NULL,
    map_id integer NOT NULL,
    parent_version_id integer,
    version integer NOT NULL,
    name character varying(160),
    width integer NOT NULL,
    height integer NOT NULL,
    hex_size integer NOT NULL,
    effective_from_game_minute bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    default_terrain_key character varying(80)
);


--
-- Name: map_versions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.map_versions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: map_versions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.map_versions_id_seq OWNED BY public.map_versions.id;


--
-- Name: maps; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.maps (
    id integer NOT NULL,
    campaign_id integer NOT NULL,
    name character varying(160) NOT NULL,
    description text,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: maps_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.maps_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: maps_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.maps_id_seq OWNED BY public.maps.id;


--
-- Name: movements; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.movements (
    id integer NOT NULL,
    expedition_id integer NOT NULL,
    map_version_id integer NOT NULL,
    from_q integer NOT NULL,
    from_r integer NOT NULL,
    to_q integer NOT NULL,
    to_r integer NOT NULL,
    departure_game_minute bigint NOT NULL,
    arrival_game_minute bigint NOT NULL,
    base_duration_minutes integer NOT NULL,
    effective_duration_minutes integer NOT NULL,
    modifiers json NOT NULL,
    CONSTRAINT ck_movement_time_order CHECK ((arrival_game_minute >= departure_game_minute))
);


--
-- Name: movements_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.movements_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: movements_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.movements_id_seq OWNED BY public.movements.id;


--
-- Name: points_of_interest; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.points_of_interest (
    id integer NOT NULL,
    hex_id integer NOT NULL,
    name character varying(160) NOT NULL,
    kind character varying(80),
    dm_description text,
    is_landmark boolean NOT NULL,
    feature_id integer NOT NULL,
    is_hub boolean DEFAULT false NOT NULL,
    player_description text,
    requires_discovery boolean DEFAULT false NOT NULL
);


--
-- Name: points_of_interest_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.points_of_interest_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: points_of_interest_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.points_of_interest_id_seq OWNED BY public.points_of_interest.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id integer NOT NULL,
    username character varying(80) NOT NULL,
    email character varying(320) NOT NULL,
    password_hash character varying(255) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    ping_color character varying(7) DEFAULT '#ff4f64'::character varying NOT NULL
);


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: wiki_pages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.wiki_pages (
    id integer NOT NULL,
    campaign_id integer NOT NULL,
    slug character varying(180) NOT NULL,
    title character varying(200) NOT NULL,
    category character varying(100)
);


--
-- Name: wiki_pages_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.wiki_pages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: wiki_pages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.wiki_pages_id_seq OWNED BY public.wiki_pages.id;


--
-- Name: wiki_revisions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.wiki_revisions (
    id integer NOT NULL,
    page_id integer NOT NULL,
    revision integer NOT NULL,
    effective_from_game_minute bigint NOT NULL,
    source_report_id integer,
    content text NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: wiki_revisions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.wiki_revisions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: wiki_revisions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.wiki_revisions_id_seq OWNED BY public.wiki_revisions.id;


--
-- Name: world_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.world_events (
    id integer NOT NULL,
    campaign_id integer NOT NULL,
    expedition_id integer,
    game_minute bigint NOT NULL,
    event_type character varying(120) NOT NULL,
    target_type character varying(80),
    target_id integer,
    payload json NOT NULL,
    dm_note text
);


--
-- Name: world_events_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.world_events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: world_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.world_events_id_seq OWNED BY public.world_events.id;


--
-- Name: campaign_invitations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_invitations ALTER COLUMN id SET DEFAULT nextval('public.campaign_invitations_id_seq'::regclass);


--
-- Name: campaign_memberships id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_memberships ALTER COLUMN id SET DEFAULT nextval('public.campaign_memberships_id_seq'::regclass);


--
-- Name: campaigns id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaigns ALTER COLUMN id SET DEFAULT nextval('public.campaigns_id_seq'::regclass);


--
-- Name: character_knowledge_observations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.character_knowledge_observations ALTER COLUMN id SET DEFAULT nextval('public.character_knowledge_observations_id_seq'::regclass);


--
-- Name: character_map_hex_observations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.character_map_hex_observations ALTER COLUMN id SET DEFAULT nextval('public.character_map_hex_observations_id_seq'::regclass);


--
-- Name: character_sheet_data_versions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.character_sheet_data_versions ALTER COLUMN id SET DEFAULT nextval('public.character_sheet_data_versions_id_seq'::regclass);


--
-- Name: character_sheet_versions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.character_sheet_versions ALTER COLUMN id SET DEFAULT nextval('public.character_sheet_versions_id_seq'::regclass);


--
-- Name: characters id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.characters ALTER COLUMN id SET DEFAULT nextval('public.characters_id_seq'::regclass);


--
-- Name: debrief_answers id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.debrief_answers ALTER COLUMN id SET DEFAULT nextval('public.debrief_answers_id_seq'::regclass);


--
-- Name: debrief_questions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.debrief_questions ALTER COLUMN id SET DEFAULT nextval('public.debrief_questions_id_seq'::regclass);


--
-- Name: debrief_templates id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.debrief_templates ALTER COLUMN id SET DEFAULT nextval('public.debrief_templates_id_seq'::regclass);


--
-- Name: expedition_characters id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expedition_characters ALTER COLUMN id SET DEFAULT nextval('public.expedition_characters_id_seq'::regclass);


--
-- Name: expedition_reports id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expedition_reports ALTER COLUMN id SET DEFAULT nextval('public.expedition_reports_id_seq'::regclass);


--
-- Name: expeditions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expeditions ALTER COLUMN id SET DEFAULT nextval('public.expeditions_id_seq'::regclass);


--
-- Name: knowledge_recalls id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.knowledge_recalls ALTER COLUMN id SET DEFAULT nextval('public.knowledge_recalls_id_seq'::regclass);


--
-- Name: map_areas id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.map_areas ALTER COLUMN id SET DEFAULT nextval('public.map_areas_id_seq'::regclass);


--
-- Name: map_edges id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.map_edges ALTER COLUMN id SET DEFAULT nextval('public.map_edges_id_seq'::regclass);


--
-- Name: map_features id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.map_features ALTER COLUMN id SET DEFAULT nextval('public.map_features_id_seq'::regclass);


--
-- Name: map_hexes id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.map_hexes ALTER COLUMN id SET DEFAULT nextval('public.map_hexes_id_seq'::regclass);


--
-- Name: map_versions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.map_versions ALTER COLUMN id SET DEFAULT nextval('public.map_versions_id_seq'::regclass);


--
-- Name: maps id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.maps ALTER COLUMN id SET DEFAULT nextval('public.maps_id_seq'::regclass);


--
-- Name: movements id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movements ALTER COLUMN id SET DEFAULT nextval('public.movements_id_seq'::regclass);


--
-- Name: points_of_interest id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.points_of_interest ALTER COLUMN id SET DEFAULT nextval('public.points_of_interest_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: wiki_pages id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wiki_pages ALTER COLUMN id SET DEFAULT nextval('public.wiki_pages_id_seq'::regclass);


--
-- Name: wiki_revisions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wiki_revisions ALTER COLUMN id SET DEFAULT nextval('public.wiki_revisions_id_seq'::regclass);


--
-- Name: world_events id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.world_events ALTER COLUMN id SET DEFAULT nextval('public.world_events_id_seq'::regclass);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: campaign_invitations campaign_invitations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_invitations
    ADD CONSTRAINT campaign_invitations_pkey PRIMARY KEY (id);


--
-- Name: campaign_memberships campaign_memberships_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_memberships
    ADD CONSTRAINT campaign_memberships_pkey PRIMARY KEY (id);


--
-- Name: campaigns campaigns_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaigns
    ADD CONSTRAINT campaigns_pkey PRIMARY KEY (id);


--
-- Name: character_knowledge_observations character_knowledge_observations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.character_knowledge_observations
    ADD CONSTRAINT character_knowledge_observations_pkey PRIMARY KEY (id);


--
-- Name: character_map_hex_observations character_map_hex_observations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.character_map_hex_observations
    ADD CONSTRAINT character_map_hex_observations_pkey PRIMARY KEY (id);


--
-- Name: character_sheet_data_versions character_sheet_data_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.character_sheet_data_versions
    ADD CONSTRAINT character_sheet_data_versions_pkey PRIMARY KEY (id);


--
-- Name: character_sheet_versions character_sheet_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.character_sheet_versions
    ADD CONSTRAINT character_sheet_versions_pkey PRIMARY KEY (id);


--
-- Name: characters characters_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.characters
    ADD CONSTRAINT characters_pkey PRIMARY KEY (id);


--
-- Name: debrief_answers debrief_answers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.debrief_answers
    ADD CONSTRAINT debrief_answers_pkey PRIMARY KEY (id);


--
-- Name: debrief_questions debrief_questions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.debrief_questions
    ADD CONSTRAINT debrief_questions_pkey PRIMARY KEY (id);


--
-- Name: debrief_templates debrief_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.debrief_templates
    ADD CONSTRAINT debrief_templates_pkey PRIMARY KEY (id);


--
-- Name: expedition_characters expedition_characters_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expedition_characters
    ADD CONSTRAINT expedition_characters_pkey PRIMARY KEY (id);


--
-- Name: expedition_reports expedition_reports_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expedition_reports
    ADD CONSTRAINT expedition_reports_pkey PRIMARY KEY (id);


--
-- Name: expeditions expeditions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expeditions
    ADD CONSTRAINT expeditions_pkey PRIMARY KEY (id);


--
-- Name: knowledge_recalls knowledge_recalls_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.knowledge_recalls
    ADD CONSTRAINT knowledge_recalls_pkey PRIMARY KEY (id);


--
-- Name: map_areas map_areas_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.map_areas
    ADD CONSTRAINT map_areas_pkey PRIMARY KEY (id);


--
-- Name: map_edges map_edges_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.map_edges
    ADD CONSTRAINT map_edges_pkey PRIMARY KEY (id);


--
-- Name: map_features map_features_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.map_features
    ADD CONSTRAINT map_features_pkey PRIMARY KEY (id);


--
-- Name: map_hexes map_hexes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.map_hexes
    ADD CONSTRAINT map_hexes_pkey PRIMARY KEY (id);


--
-- Name: map_versions map_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.map_versions
    ADD CONSTRAINT map_versions_pkey PRIMARY KEY (id);


--
-- Name: maps maps_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.maps
    ADD CONSTRAINT maps_pkey PRIMARY KEY (id);


--
-- Name: movements movements_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movements
    ADD CONSTRAINT movements_pkey PRIMARY KEY (id);


--
-- Name: points_of_interest points_of_interest_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.points_of_interest
    ADD CONSTRAINT points_of_interest_pkey PRIMARY KEY (id);


--
-- Name: campaign_invitations uq_campaign_invitation_user; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_invitations
    ADD CONSTRAINT uq_campaign_invitation_user UNIQUE (campaign_id, invited_user_id);


--
-- Name: campaign_memberships uq_campaign_membership; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_memberships
    ADD CONSTRAINT uq_campaign_membership UNIQUE (campaign_id, user_id);


--
-- Name: character_knowledge_observations uq_character_knowledge_observation; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.character_knowledge_observations
    ADD CONSTRAINT uq_character_knowledge_observation UNIQUE (character_id, target_type, target_id, observed_game_minute, expedition_id);


--
-- Name: character_map_hex_observations uq_character_map_hex_observation; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.character_map_hex_observations
    ADD CONSTRAINT uq_character_map_hex_observation UNIQUE (character_id, map_id, q, r, observed_game_minute, expedition_id);


--
-- Name: character_sheet_data_versions uq_character_sheet_data_version; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.character_sheet_data_versions
    ADD CONSTRAINT uq_character_sheet_data_version UNIQUE (character_id, version);


--
-- Name: character_sheet_versions uq_character_sheet_version; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.character_sheet_versions
    ADD CONSTRAINT uq_character_sheet_version UNIQUE (character_id, version);


--
-- Name: debrief_answers uq_debrief_answer; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.debrief_answers
    ADD CONSTRAINT uq_debrief_answer UNIQUE (expedition_id, question_id, character_id);


--
-- Name: expedition_characters uq_expedition_character; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expedition_characters
    ADD CONSTRAINT uq_expedition_character UNIQUE (expedition_id, character_id);


--
-- Name: knowledge_recalls uq_knowledge_recall_page; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.knowledge_recalls
    ADD CONSTRAINT uq_knowledge_recall_page UNIQUE (expedition_id, character_id, page_id);


--
-- Name: map_areas uq_map_area_feature; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.map_areas
    ADD CONSTRAINT uq_map_area_feature UNIQUE (map_version_id, feature_type, feature_id);


--
-- Name: map_edges uq_map_edge_feature_coordinates; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.map_edges
    ADD CONSTRAINT uq_map_edge_feature_coordinates UNIQUE (map_version_id, from_q, from_r, to_q, to_r, feature_type, feature_id);


--
-- Name: map_features uq_map_feature_campaign_type_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.map_features
    ADD CONSTRAINT uq_map_feature_campaign_type_id UNIQUE (campaign_id, feature_type, feature_id);


--
-- Name: map_hexes uq_map_hex_coordinate; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.map_hexes
    ADD CONSTRAINT uq_map_hex_coordinate UNIQUE (map_version_id, q, r);


--
-- Name: map_versions uq_map_version; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.map_versions
    ADD CONSTRAINT uq_map_version UNIQUE (map_id, version);


--
-- Name: wiki_pages uq_wiki_campaign_slug; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wiki_pages
    ADD CONSTRAINT uq_wiki_campaign_slug UNIQUE (campaign_id, slug);


--
-- Name: wiki_revisions uq_wiki_revision; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wiki_revisions
    ADD CONSTRAINT uq_wiki_revision UNIQUE (page_id, revision);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: wiki_pages wiki_pages_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wiki_pages
    ADD CONSTRAINT wiki_pages_pkey PRIMARY KEY (id);


--
-- Name: wiki_revisions wiki_revisions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wiki_revisions
    ADD CONSTRAINT wiki_revisions_pkey PRIMARY KEY (id);


--
-- Name: world_events world_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.world_events
    ADD CONSTRAINT world_events_pkey PRIMARY KEY (id);


--
-- Name: ix_campaign_invitations_campaign_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_campaign_invitations_campaign_id ON public.campaign_invitations USING btree (campaign_id);


--
-- Name: ix_campaign_invitations_invited_by_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_campaign_invitations_invited_by_user_id ON public.campaign_invitations USING btree (invited_by_user_id);


--
-- Name: ix_campaign_invitations_invited_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_campaign_invitations_invited_user_id ON public.campaign_invitations USING btree (invited_user_id);


--
-- Name: ix_campaign_invitations_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_campaign_invitations_status ON public.campaign_invitations USING btree (status);


--
-- Name: ix_campaign_memberships_campaign_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_campaign_memberships_campaign_id ON public.campaign_memberships USING btree (campaign_id);


--
-- Name: ix_campaign_memberships_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_campaign_memberships_user_id ON public.campaign_memberships USING btree (user_id);


--
-- Name: ix_character_knowledge_observations_character_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_character_knowledge_observations_character_id ON public.character_knowledge_observations USING btree (character_id);


--
-- Name: ix_character_knowledge_observations_expedition_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_character_knowledge_observations_expedition_id ON public.character_knowledge_observations USING btree (expedition_id);


--
-- Name: ix_character_knowledge_observations_observed_game_minute; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_character_knowledge_observations_observed_game_minute ON public.character_knowledge_observations USING btree (observed_game_minute);


--
-- Name: ix_character_knowledge_observations_target_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_character_knowledge_observations_target_id ON public.character_knowledge_observations USING btree (target_id);


--
-- Name: ix_character_knowledge_observations_target_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_character_knowledge_observations_target_type ON public.character_knowledge_observations USING btree (target_type);


--
-- Name: ix_character_map_hex_observations_character_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_character_map_hex_observations_character_id ON public.character_map_hex_observations USING btree (character_id);


--
-- Name: ix_character_map_hex_observations_expedition_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_character_map_hex_observations_expedition_id ON public.character_map_hex_observations USING btree (expedition_id);


--
-- Name: ix_character_map_hex_observations_map_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_character_map_hex_observations_map_id ON public.character_map_hex_observations USING btree (map_id);


--
-- Name: ix_character_map_hex_observations_map_version_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_character_map_hex_observations_map_version_id ON public.character_map_hex_observations USING btree (map_version_id);


--
-- Name: ix_character_map_hex_observations_observed_game_minute; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_character_map_hex_observations_observed_game_minute ON public.character_map_hex_observations USING btree (observed_game_minute);


--
-- Name: ix_character_map_hex_observations_q; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_character_map_hex_observations_q ON public.character_map_hex_observations USING btree (q);


--
-- Name: ix_character_map_hex_observations_r; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_character_map_hex_observations_r ON public.character_map_hex_observations USING btree (r);


--
-- Name: ix_character_sheet_data_versions_character_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_character_sheet_data_versions_character_id ON public.character_sheet_data_versions USING btree (character_id);


--
-- Name: ix_character_sheet_versions_character_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_character_sheet_versions_character_id ON public.character_sheet_versions USING btree (character_id);


--
-- Name: ix_character_sheet_versions_expedition_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_character_sheet_versions_expedition_id ON public.character_sheet_versions USING btree (expedition_id);


--
-- Name: ix_characters_campaign_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_characters_campaign_id ON public.characters USING btree (campaign_id);


--
-- Name: ix_characters_owner_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_characters_owner_user_id ON public.characters USING btree (owner_user_id);


--
-- Name: ix_debrief_answers_character_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_debrief_answers_character_id ON public.debrief_answers USING btree (character_id);


--
-- Name: ix_debrief_answers_expedition_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_debrief_answers_expedition_id ON public.debrief_answers USING btree (expedition_id);


--
-- Name: ix_debrief_questions_template_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_debrief_questions_template_id ON public.debrief_questions USING btree (template_id);


--
-- Name: ix_debrief_templates_campaign_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_debrief_templates_campaign_id ON public.debrief_templates USING btree (campaign_id);


--
-- Name: ix_expedition_characters_character_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_expedition_characters_character_id ON public.expedition_characters USING btree (character_id);


--
-- Name: ix_expedition_characters_expedition_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_expedition_characters_expedition_id ON public.expedition_characters USING btree (expedition_id);


--
-- Name: ix_expedition_reports_expedition_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_expedition_reports_expedition_id ON public.expedition_reports USING btree (expedition_id);


--
-- Name: ix_expedition_reports_published_game_minute; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_expedition_reports_published_game_minute ON public.expedition_reports USING btree (published_game_minute);


--
-- Name: ix_expeditions_campaign_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_expeditions_campaign_id ON public.expeditions USING btree (campaign_id);


--
-- Name: ix_expeditions_dm_ping_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_expeditions_dm_ping_user_id ON public.expeditions USING btree (dm_ping_user_id);


--
-- Name: ix_expeditions_ping_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_expeditions_ping_user_id ON public.expeditions USING btree (ping_user_id);


--
-- Name: ix_expeditions_return_game_minute; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_expeditions_return_game_minute ON public.expeditions USING btree (return_game_minute);


--
-- Name: ix_knowledge_recalls_character_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_knowledge_recalls_character_id ON public.knowledge_recalls USING btree (character_id);


--
-- Name: ix_knowledge_recalls_expedition_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_knowledge_recalls_expedition_id ON public.knowledge_recalls USING btree (expedition_id);


--
-- Name: ix_knowledge_recalls_page_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_knowledge_recalls_page_id ON public.knowledge_recalls USING btree (page_id);


--
-- Name: ix_map_areas_feature; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_map_areas_feature ON public.map_areas USING btree (feature_type, feature_id);


--
-- Name: ix_map_areas_map_version_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_map_areas_map_version_id ON public.map_areas USING btree (map_version_id);


--
-- Name: ix_map_edges_feature_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_map_edges_feature_id ON public.map_edges USING btree (feature_id);


--
-- Name: ix_map_edges_feature_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_map_edges_feature_type ON public.map_edges USING btree (feature_type);


--
-- Name: ix_map_edges_map_version_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_map_edges_map_version_id ON public.map_edges USING btree (map_version_id);


--
-- Name: ix_map_features_campaign_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_map_features_campaign_id ON public.map_features USING btree (campaign_id);


--
-- Name: ix_map_features_downstream_feature_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_map_features_downstream_feature_id ON public.map_features USING btree (downstream_feature_id);


--
-- Name: ix_map_features_downstream_feature_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_map_features_downstream_feature_type ON public.map_features USING btree (downstream_feature_type);


--
-- Name: ix_map_features_feature_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_map_features_feature_id ON public.map_features USING btree (feature_id);


--
-- Name: ix_map_features_feature_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_map_features_feature_type ON public.map_features USING btree (feature_type);


--
-- Name: ix_map_features_map_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_map_features_map_id ON public.map_features USING btree (map_id);


--
-- Name: ix_map_hexes_map_version_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_map_hexes_map_version_id ON public.map_hexes USING btree (map_version_id);


--
-- Name: ix_map_versions_effective_from_game_minute; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_map_versions_effective_from_game_minute ON public.map_versions USING btree (effective_from_game_minute);


--
-- Name: ix_map_versions_map_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_map_versions_map_id ON public.map_versions USING btree (map_id);


--
-- Name: ix_maps_campaign_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_maps_campaign_id ON public.maps USING btree (campaign_id);


--
-- Name: ix_movements_arrival_game_minute; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_movements_arrival_game_minute ON public.movements USING btree (arrival_game_minute);


--
-- Name: ix_movements_departure_game_minute; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_movements_departure_game_minute ON public.movements USING btree (departure_game_minute);


--
-- Name: ix_movements_expedition_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_movements_expedition_id ON public.movements USING btree (expedition_id);


--
-- Name: ix_movements_map_version_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_movements_map_version_id ON public.movements USING btree (map_version_id);


--
-- Name: ix_points_of_interest_feature_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_points_of_interest_feature_id ON public.points_of_interest USING btree (feature_id);


--
-- Name: ix_points_of_interest_hex_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_points_of_interest_hex_id ON public.points_of_interest USING btree (hex_id);


--
-- Name: ix_points_of_interest_is_hub; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_points_of_interest_is_hub ON public.points_of_interest USING btree (is_hub);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_username; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_username ON public.users USING btree (username);


--
-- Name: ix_wiki_pages_campaign_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_wiki_pages_campaign_id ON public.wiki_pages USING btree (campaign_id);


--
-- Name: ix_wiki_revisions_effective_from_game_minute; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_wiki_revisions_effective_from_game_minute ON public.wiki_revisions USING btree (effective_from_game_minute);


--
-- Name: ix_wiki_revisions_page_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_wiki_revisions_page_id ON public.wiki_revisions USING btree (page_id);


--
-- Name: ix_world_events_campaign_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_world_events_campaign_id ON public.world_events USING btree (campaign_id);


--
-- Name: ix_world_events_event_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_world_events_event_type ON public.world_events USING btree (event_type);


--
-- Name: ix_world_events_expedition_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_world_events_expedition_id ON public.world_events USING btree (expedition_id);


--
-- Name: ix_world_events_game_minute; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_world_events_game_minute ON public.world_events USING btree (game_minute);


--
-- Name: campaign_invitations campaign_invitations_campaign_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_invitations
    ADD CONSTRAINT campaign_invitations_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES public.campaigns(id) ON DELETE CASCADE;


--
-- Name: campaign_invitations campaign_invitations_invited_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_invitations
    ADD CONSTRAINT campaign_invitations_invited_by_user_id_fkey FOREIGN KEY (invited_by_user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: campaign_invitations campaign_invitations_invited_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_invitations
    ADD CONSTRAINT campaign_invitations_invited_user_id_fkey FOREIGN KEY (invited_user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: campaign_memberships campaign_memberships_campaign_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_memberships
    ADD CONSTRAINT campaign_memberships_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES public.campaigns(id) ON DELETE CASCADE;


--
-- Name: campaign_memberships campaign_memberships_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_memberships
    ADD CONSTRAINT campaign_memberships_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: character_knowledge_observations character_knowledge_observations_character_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.character_knowledge_observations
    ADD CONSTRAINT character_knowledge_observations_character_id_fkey FOREIGN KEY (character_id) REFERENCES public.characters(id) ON DELETE CASCADE;


--
-- Name: character_knowledge_observations character_knowledge_observations_expedition_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.character_knowledge_observations
    ADD CONSTRAINT character_knowledge_observations_expedition_id_fkey FOREIGN KEY (expedition_id) REFERENCES public.expeditions(id) ON DELETE SET NULL;


--
-- Name: character_map_hex_observations character_map_hex_observations_character_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.character_map_hex_observations
    ADD CONSTRAINT character_map_hex_observations_character_id_fkey FOREIGN KEY (character_id) REFERENCES public.characters(id) ON DELETE CASCADE;


--
-- Name: character_map_hex_observations character_map_hex_observations_expedition_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.character_map_hex_observations
    ADD CONSTRAINT character_map_hex_observations_expedition_id_fkey FOREIGN KEY (expedition_id) REFERENCES public.expeditions(id) ON DELETE SET NULL;


--
-- Name: character_map_hex_observations character_map_hex_observations_map_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.character_map_hex_observations
    ADD CONSTRAINT character_map_hex_observations_map_id_fkey FOREIGN KEY (map_id) REFERENCES public.maps(id) ON DELETE CASCADE;


--
-- Name: character_map_hex_observations character_map_hex_observations_map_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.character_map_hex_observations
    ADD CONSTRAINT character_map_hex_observations_map_version_id_fkey FOREIGN KEY (map_version_id) REFERENCES public.map_versions(id) ON DELETE RESTRICT;


--
-- Name: character_sheet_data_versions character_sheet_data_versions_character_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.character_sheet_data_versions
    ADD CONSTRAINT character_sheet_data_versions_character_id_fkey FOREIGN KEY (character_id) REFERENCES public.characters(id) ON DELETE CASCADE;


--
-- Name: character_sheet_versions character_sheet_versions_character_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.character_sheet_versions
    ADD CONSTRAINT character_sheet_versions_character_id_fkey FOREIGN KEY (character_id) REFERENCES public.characters(id) ON DELETE CASCADE;


--
-- Name: character_sheet_versions character_sheet_versions_expedition_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.character_sheet_versions
    ADD CONSTRAINT character_sheet_versions_expedition_id_fkey FOREIGN KEY (expedition_id) REFERENCES public.expeditions(id) ON DELETE SET NULL;


--
-- Name: characters characters_campaign_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.characters
    ADD CONSTRAINT characters_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES public.campaigns(id) ON DELETE CASCADE;


--
-- Name: characters characters_owner_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.characters
    ADD CONSTRAINT characters_owner_user_id_fkey FOREIGN KEY (owner_user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: debrief_answers debrief_answers_character_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.debrief_answers
    ADD CONSTRAINT debrief_answers_character_id_fkey FOREIGN KEY (character_id) REFERENCES public.characters(id) ON DELETE CASCADE;


--
-- Name: debrief_answers debrief_answers_expedition_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.debrief_answers
    ADD CONSTRAINT debrief_answers_expedition_id_fkey FOREIGN KEY (expedition_id) REFERENCES public.expeditions(id) ON DELETE CASCADE;


--
-- Name: debrief_answers debrief_answers_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.debrief_answers
    ADD CONSTRAINT debrief_answers_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.debrief_questions(id) ON DELETE CASCADE;


--
-- Name: debrief_questions debrief_questions_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.debrief_questions
    ADD CONSTRAINT debrief_questions_template_id_fkey FOREIGN KEY (template_id) REFERENCES public.debrief_templates(id) ON DELETE CASCADE;


--
-- Name: debrief_templates debrief_templates_campaign_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.debrief_templates
    ADD CONSTRAINT debrief_templates_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES public.campaigns(id) ON DELETE CASCADE;


--
-- Name: expedition_characters expedition_characters_character_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expedition_characters
    ADD CONSTRAINT expedition_characters_character_id_fkey FOREIGN KEY (character_id) REFERENCES public.characters(id) ON DELETE CASCADE;


--
-- Name: expedition_characters expedition_characters_expedition_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expedition_characters
    ADD CONSTRAINT expedition_characters_expedition_id_fkey FOREIGN KEY (expedition_id) REFERENCES public.expeditions(id) ON DELETE CASCADE;


--
-- Name: expedition_reports expedition_reports_expedition_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expedition_reports
    ADD CONSTRAINT expedition_reports_expedition_id_fkey FOREIGN KEY (expedition_id) REFERENCES public.expeditions(id) ON DELETE CASCADE;


--
-- Name: expeditions expeditions_campaign_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expeditions
    ADD CONSTRAINT expeditions_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES public.campaigns(id) ON DELETE CASCADE;


--
-- Name: expeditions expeditions_current_map_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expeditions
    ADD CONSTRAINT expeditions_current_map_version_id_fkey FOREIGN KEY (current_map_version_id) REFERENCES public.map_versions(id) ON DELETE SET NULL;


--
-- Name: expeditions fk_expeditions_dm_ping_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expeditions
    ADD CONSTRAINT fk_expeditions_dm_ping_user FOREIGN KEY (dm_ping_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: expeditions fk_expeditions_ping_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expeditions
    ADD CONSTRAINT fk_expeditions_ping_user FOREIGN KEY (ping_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: knowledge_recalls knowledge_recalls_character_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.knowledge_recalls
    ADD CONSTRAINT knowledge_recalls_character_id_fkey FOREIGN KEY (character_id) REFERENCES public.characters(id) ON DELETE CASCADE;


--
-- Name: knowledge_recalls knowledge_recalls_expedition_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.knowledge_recalls
    ADD CONSTRAINT knowledge_recalls_expedition_id_fkey FOREIGN KEY (expedition_id) REFERENCES public.expeditions(id) ON DELETE CASCADE;


--
-- Name: knowledge_recalls knowledge_recalls_page_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.knowledge_recalls
    ADD CONSTRAINT knowledge_recalls_page_id_fkey FOREIGN KEY (page_id) REFERENCES public.wiki_pages(id) ON DELETE CASCADE;


--
-- Name: map_areas map_areas_map_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.map_areas
    ADD CONSTRAINT map_areas_map_version_id_fkey FOREIGN KEY (map_version_id) REFERENCES public.map_versions(id) ON DELETE CASCADE;


--
-- Name: map_edges map_edges_map_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.map_edges
    ADD CONSTRAINT map_edges_map_version_id_fkey FOREIGN KEY (map_version_id) REFERENCES public.map_versions(id) ON DELETE CASCADE;


--
-- Name: map_features map_features_campaign_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.map_features
    ADD CONSTRAINT map_features_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES public.campaigns(id) ON DELETE CASCADE;


--
-- Name: map_features map_features_map_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.map_features
    ADD CONSTRAINT map_features_map_id_fkey FOREIGN KEY (map_id) REFERENCES public.maps(id) ON DELETE CASCADE;


--
-- Name: map_hexes map_hexes_map_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.map_hexes
    ADD CONSTRAINT map_hexes_map_version_id_fkey FOREIGN KEY (map_version_id) REFERENCES public.map_versions(id) ON DELETE CASCADE;


--
-- Name: map_versions map_versions_map_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.map_versions
    ADD CONSTRAINT map_versions_map_id_fkey FOREIGN KEY (map_id) REFERENCES public.maps(id) ON DELETE CASCADE;


--
-- Name: map_versions map_versions_parent_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.map_versions
    ADD CONSTRAINT map_versions_parent_version_id_fkey FOREIGN KEY (parent_version_id) REFERENCES public.map_versions(id) ON DELETE SET NULL;


--
-- Name: maps maps_campaign_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.maps
    ADD CONSTRAINT maps_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES public.campaigns(id) ON DELETE CASCADE;


--
-- Name: movements movements_expedition_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movements
    ADD CONSTRAINT movements_expedition_id_fkey FOREIGN KEY (expedition_id) REFERENCES public.expeditions(id) ON DELETE CASCADE;


--
-- Name: movements movements_map_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movements
    ADD CONSTRAINT movements_map_version_id_fkey FOREIGN KEY (map_version_id) REFERENCES public.map_versions(id) ON DELETE RESTRICT;


--
-- Name: points_of_interest points_of_interest_hex_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.points_of_interest
    ADD CONSTRAINT points_of_interest_hex_id_fkey FOREIGN KEY (hex_id) REFERENCES public.map_hexes(id) ON DELETE CASCADE;


--
-- Name: wiki_pages wiki_pages_campaign_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wiki_pages
    ADD CONSTRAINT wiki_pages_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES public.campaigns(id) ON DELETE CASCADE;


--
-- Name: wiki_revisions wiki_revisions_page_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wiki_revisions
    ADD CONSTRAINT wiki_revisions_page_id_fkey FOREIGN KEY (page_id) REFERENCES public.wiki_pages(id) ON DELETE CASCADE;


--
-- Name: wiki_revisions wiki_revisions_source_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wiki_revisions
    ADD CONSTRAINT wiki_revisions_source_report_id_fkey FOREIGN KEY (source_report_id) REFERENCES public.expedition_reports(id) ON DELETE SET NULL;


--
-- Name: world_events world_events_campaign_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.world_events
    ADD CONSTRAINT world_events_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES public.campaigns(id) ON DELETE CASCADE;


--
-- Name: world_events world_events_expedition_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.world_events
    ADD CONSTRAINT world_events_expedition_id_fkey FOREIGN KEY (expedition_id) REFERENCES public.expeditions(id) ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--

\unrestrict chMIhVeTmL4RsKuCDq0qvM9a75pdecwjihgYZnpFEUot8QQVABjEqJbzTefJrVz

