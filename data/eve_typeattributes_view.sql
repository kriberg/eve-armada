--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = off;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET escape_string_warning = off;

SET search_path = public, pg_catalog;

--
-- Name: eve_typeattributes_view; Type: VIEW; Schema: public; Owner: armada
--

CREATE VIEW eve_typeattributes_view AS
    SELECT at.attributeid, ta.typeid, ac.categoryname, ac.categorydescription, at.displayname, ta.valueint, ta.valuefloat, at.iconid FROM dgmtypeattributes ta, dgmattributetypes at, dgmattributecategories ac WHERE (((((at.attributeid = ta.attributeid) AND (ac.categoryid = at.categoryid)) AND (at.published = 1)) AND (at.displayname IS NOT NULL)) AND ((ac.categoryname)::text <> 'NULL'::text));


ALTER TABLE public.eve_typeattributes_view OWNER TO armada;

--
-- PostgreSQL database dump complete
--

