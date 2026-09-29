import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Network, ArrowRight, RefreshCcw, Loader2 } from "lucide-react";
import { Card, PageHeader, Metric, Button, Badge } from "../../components/ui";
import { useSdodState } from "../../state/SdodState";
import { sdodEndpoints } from "../../api/sdodClient";

export default function SchemaBuilder() {
  const { schema, setSchema, generateSchema, notify, status } = useSdodState();
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    if (!schema && status.has_schema) {
      sdodEndpoints.getSchema().then((res) => setSchema(res.data)).catch(() => {});
    } else if (!schema && status.has_answers) {
      handleGenerate();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleGenerate = async () => {
    setLoading(true);
    try {
      await generateSchema();
      notify("Schema generated.", "success");
    } catch (err) {
      notify(err?.response?.data?.detail || "Failed to generate schema — complete Step 1 first.", "error");
    } finally {
      setLoading(false);
    }
  };

  if (!status.has_answers && !schema) {
    return (
      <div>
        <PageHeader icon={Network} title="Step 2 — Schema Generation" subtitle="Build a relational schema from your intent." />
        <Card>
          <p className="text-sm text-slate-400">
            Complete the <strong className="text-slate-200">Define Intent</strong> step first so we know what kind
            of schema to build.
          </p>
        </Card>
      </div>
    );
  }

  const totalColumns = schema ? schema.tables.reduce((sum, t) => sum + t.columns.length, 0) : 0;

  return (
    <div>
      <PageHeader
        icon={Network}
        title="Step 2 — Schema Generation"
        subtitle="A relational schema was generated from your intent and calibration answers."
        right={
          <Button variant="secondary" onClick={handleGenerate} disabled={loading}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCcw className="h-4 w-4" />}
            Regenerate
          </Button>
        }
      />

      {schema && (
        <>
          <div className="mb-6 grid grid-cols-3 gap-4">
            <Metric label="Tables" value={schema.tables.length} accent="brand" />
            <Metric label="Total Columns" value={totalColumns} accent="emerald" />
            <Metric label="Relationships" value={(schema.relationships || []).length} accent="purple" />
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {schema.tables.map((table) => (
              <Card key={table.name}>
                <div className="mb-2 flex items-center justify-between">
                  <h3 className="font-semibold text-white">{table.name}</h3>
                  <Badge tone="slate">{table.columns.length} cols</Badge>
                </div>
                <ul className="space-y-1 text-xs text-slate-400">
                  {table.columns.map((col) => (
                    <li key={col.name} className="flex items-center justify-between gap-2">
                      <span className="truncate text-slate-300">{col.name}</span>
                      <span className="shrink-0 text-slate-500">{col.type}</span>
                    </li>
                  ))}
                </ul>
                {table.foreign_keys.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {table.foreign_keys.map((fk) => (
                      <Badge key={fk.column} tone="amber">
                        {fk.column} → {fk.references}
                      </Badge>
                    ))}
                  </div>
                )}
              </Card>
            ))}
          </div>

          <div className="mt-6 flex items-center gap-3">
            <Button onClick={() => navigate("/sdod/editor")}>
              Edit Schema
              <ArrowRight className="h-4 w-4" />
            </Button>
            <Button variant="secondary" onClick={() => navigate("/sdod/generate")}>
              Skip to Data Generation
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
