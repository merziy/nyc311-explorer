from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "complaints" (
    "unique_key" BIGINT NOT NULL  PRIMARY KEY,
    "created_date" TIMESTAMPTZ NOT NULL,
    "closed_date" TIMESTAMPTZ,
    "complaint_type" TEXT NOT NULL,
    "descriptor" TEXT,
    "borough" VARCHAR(20) CHECK ("borough" IN ('MANHATTAN','BRONX','BROOKLYN','QUEENS','STATEN ISLAND')),
    "incident_zip" TEXT,
    "agency" TEXT,
    "status" TEXT,
    "latitude" DOUBLE PRECISION,
    "longitude" DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS "idx_complaints_created_74580f" ON "complaints" ("created_date");
CREATE INDEX IF NOT EXISTS "idx_complaints_borough_0518c9" ON "complaints" ("borough", "created_date");
CREATE INDEX IF NOT EXISTS "idx_complaints_complai_e0034f" ON "complaints" ("complaint_type", "created_date");
COMMENT ON COLUMN "complaints"."borough" IS 'MANHATTAN: MANHATTAN\nBRONX: BRONX\nBROOKLYN: BROOKLYN\nQUEENS: QUEENS\nSTATEN_ISLAND: STATEN ISLAND';
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
