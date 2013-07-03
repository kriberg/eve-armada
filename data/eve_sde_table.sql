CREATE TABLE "eve_sde_table" (
    "id" serial NOT NULL PRIMARY KEY,
    "batch" integer not null,
    "name" VARCHAR(50) not null,
    "updated" TIMESTAMP with time zone,
    "dumpfile" VARCHAR(200)
);
