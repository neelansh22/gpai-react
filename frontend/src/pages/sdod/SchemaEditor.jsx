import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { PencilRuler, Plus, Trash2, Save, Upload, ArrowRight } from "lucide-react";
import { Card, PageHeader, Button, Badge } from "../../components/ui";
import { useSdodState } from "../../state/SdodState";
import { sdodEndpoints } from "../../api/sdodClient";

const TYPE_OPTIONS = ["VARCHAR(255)", "INT", "BIGINT", "DATE", "TIMESTAMP", "DECIMAL(10,2)", "BOOLEAN", "TEXT", "JSON"];

function TableCard({ table, onChange, onDelete }) {
  const updateTableName = (name) => onChange({ ...table, name });

  const updateColumn = (idx, patch) => {
    const columns = table.columns.map((c, i) => (i === idx ? { ...c, ...patch } : c));
    onChange({ ...table, columns });
  };

  const addColumn = () => {
    onChange({
      ...table,
      columns: [...table.columns, { name: `new_column_${table.columns.length + 1}`, type: "VARCHAR(255)", description: "" }],
    });
  };

  const deleteColumn = (idx) => {
    onChange({ ...table, columns: table.columns.filter((_, i) => i !== idx) });
  };

  return (
    <Card>
      <div className="mb-3 flex items-center justify-between gap-2">
        <input
          value={table.name}
          onChange={(e) => updateTableName(e.target.value)}
          className="rounded-lg border border-slate-800 bg-slate-950/60 px-2 py-1 text-sm font-semibold text-white focus:border-emerald-500/50 focus:outline-none"
        />
        <button onClick={onDelete} className="rounded-lg p-1.5 text-rose-400 hover:bg-rose-500/10" title="Delete table">
          <Trash2 className="h-4 w-4" />
        </button>
      </div>

      <div className="space-y-2">
        {table.columns.map((col, idx) => (
          <div key={idx} className="flex items-center gap-2">
            <input
              value={col.name}
              onChange={(e) => updateColumn(idx, { name: e.target.value })}
              className="w-1/3 rounded-lg border border-slate-800 bg-slate-950/60 px-2 py-1 text-xs text-slate-200 focus:border-emerald-500/50 focus:outline-none"
            />
            <select
              value={col.type}
              onChange={(e) => updateColumn(idx, { type: e.target.value })}
              className="w-1/3 rounded-lg border border-slate-800 bg-slate-950/60 px-2 py-1 text-xs text-slate-300 focus:border-emerald-500/50 focus:outline-none"
            >
              {TYPE_OPTIONS.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
            <input
              value={col.description || ""}
              onChange={(e) => updateColumn(idx, { description: e.target.value })}
              placeholder="Description"
              className="flex-1 rounded-lg border border-slate-800 bg-slate-950/60 px-2 py-1 text-xs text-slate-400 placeholder:text-slate-600 focus:border-emerald-500/50 focus:outline-none"
            />
            <button onClick={() => deleteColumn(idx)} className="shrink-0 rounded-lg p-1 text-slate-500 hover:text-rose-400">
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </div>

      <button
        onClick={addColumn}
        className="mt-3 flex items-center gap-1.5 rounded-lg bg-slate-900 px-2.5 py-1.5 text-xs text-slate-400 ring-1 ring-slate-800 hover:text-slate-200"
      >
        <Plus className="h-3.5 w-3.5" /> Add Column
      </button>

      {table.foreign_keys?.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {table.foreign_keys.map((fk) => (
            <Badge key={fk.column} tone="amber">
              {fk.column} → {fk.references}
            </Badge>
          ))}
        </div>
      )}
    </Card>
  );
}

export default function SchemaEditor() {
  const { schema, setSchema, saveSchema, uploadSchema, notify, status } = useSdodState();
  const [draft, setDraft] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (schema) {
      setDraft(JSON.parse(JSON.stringify(schema)));
    } else if (status.has_schema) {
      sdodEndpoints.getSchema().then((res) => {
        setSchema(res.data);
        setDraft(JSON.parse(JSON.stringify(res.data)));
      }).catch(() => {});
    }
  }, [schema, status.has_schema, setSchema]);

  if (!draft) {
    return (
      <div>
        <PageHeader icon={PencilRuler} title="Step 3 — Edit Schema" subtitle="Fine-tune your generated schema, or upload your own." accent="emerald" tip="No schema yet? Build one in Step 2, or drop in your own JSON schema file below to skip straight to editing." />
        <Card>
          <p className="text-sm text-slate-400">
            No schema yet. Go to <strong className="text-slate-200">Build Schema</strong> first, or upload a JSON schema below.
          </p>
          <UploadBox uploadSchema={uploadSchema} notify={notify} onDone={(s) => setDraft(JSON.parse(JSON.stringify(s)))} />
        </Card>
      </div>
    );
  }

  const updateTable = (idx, next) => {
    const tables = draft.tables.map((t, i) => (i === idx ? next : t));
    setDraft({ ...draft, tables });
  };

  const deleteTable = (idx) => {
    setDraft({ ...draft, tables: draft.tables.filter((_, i) => i !== idx) });
  };

  const addTable = () => {
    setDraft({
      ...draft,
      tables: [
        ...draft.tables,
        { name: `new_table_${draft.tables.length + 1}`, columns: [{ name: "id", type: "INT", description: "Primary key" }], primary_key: ["id"], foreign_keys: [] },
      ],
    });
  };

  const handleSave = async () => {
    try {
      const saved = await saveSchema(draft);
      setDraft(JSON.parse(JSON.stringify(saved)));
      notify("Schema saved.", "success");
    } catch (err) {
      notify(err?.response?.data?.detail || "Failed to save schema", "error");
    }
  };

  return (
    <div>
      <PageHeader
        icon={PencilRuler}
        title="Step 3 — Edit Schema"
        subtitle="Rename tables/columns, adjust types, or add/remove fields."
        accent="emerald"
        tip="Directly edit table and column names, data types, and primary/foreign keys. Add or remove tables as needed, then save — your changes carry through to data generation in the next step."
        right={
          <div className="flex gap-2">
            <Button variant="secondary" onClick={addTable}>
              <Plus className="h-4 w-4" /> Add Table
            </Button>
            <Button onClick={handleSave}>
              <Save className="h-4 w-4" /> Save Schema
            </Button>
          </div>
        }
      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {draft.tables.map((table, idx) => (
          <TableCard key={idx} table={table} onChange={(next) => updateTable(idx, next)} onDelete={() => deleteTable(idx)} />
        ))}
      </div>

      <Card className="mt-6">
        <UploadBox uploadSchema={uploadSchema} notify={notify} onDone={(s) => setDraft(JSON.parse(JSON.stringify(s)))} />
      </Card>

      <div className="mt-6">
        <Button onClick={() => navigate("/sdod/generate")}>
          Continue to Data Generation
          <ArrowRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

function UploadBox({ uploadSchema, notify, onDone }) {
  const handleFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      const parsed = JSON.parse(text);
      const saved = await uploadSchema(parsed);
      onDone(saved);
      notify("Schema uploaded successfully.", "success");
    } catch (err) {
      notify(err?.response?.data?.detail || "Invalid schema JSON", "error");
    }
    e.target.value = "";
  };

  return (
    <label className="flex cursor-pointer items-center gap-2 text-xs text-slate-400 hover:text-slate-200">
      <Upload className="h-4 w-4" />
      Upload a JSON schema file (tables / columns / primary_key / foreign_keys)
      <input type="file" accept=".json,application/json" className="hidden" onChange={handleFile} />
    </label>
  );
}
