import { createContext, useCallback, useContext, useState } from "react";
import { sdodEndpoints } from "../api/sdodClient";

const SdodContext = createContext(null);

const initialStatus = {
  intent: null,
  domain: null,
  has_questions: false,
  has_answers: false,
  has_schema: false,
  schema_source: null,
  table_count: 0,
  has_data: false,
  table_names: [],
  rows_per_table: 60,
  consolidated_rows: 0,
  consolidated_cols: 0,
  has_augmented: false,
  last_rule_message: null,
};

export function SdodStateProvider({ children }) {
  const [status, setStatus] = useState(initialStatus);
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswersState] = useState({});
  const [schema, setSchema] = useState(null);
  const [toast, setToast] = useState(null);

  const notify = useCallback((message, tone = "info") => {
    setToast({ message, tone, id: Date.now() });
    window.clearTimeout(notify._t);
    notify._t = window.setTimeout(() => setToast(null), 3500);
  }, []);

  const refreshStatus = useCallback(async () => {
    try {
      const { data } = await sdodEndpoints.status();
      setStatus(data);
      return data;
    } catch (e) {
      return null;
    }
  }, []);

  const submitIntent = useCallback(
    async (intent) => {
      const { data } = await sdodEndpoints.submitIntent(intent);
      setQuestions(data.questions || []);
      setAnswersState({});
      await refreshStatus();
      return data;
    },
    [refreshStatus]
  );

  const submitAnswers = useCallback(
    async (nextAnswers) => {
      setAnswersState(nextAnswers);
      await sdodEndpoints.submitAnswers(nextAnswers);
      await refreshStatus();
    },
    [refreshStatus]
  );

  const generateSchema = useCallback(async () => {
    const { data } = await sdodEndpoints.generateSchema();
    setSchema(data);
    await refreshStatus();
    return data;
  }, [refreshStatus]);

  const saveSchema = useCallback(
    async (nextSchema) => {
      const { data } = await sdodEndpoints.updateSchema(nextSchema);
      setSchema(data);
      await refreshStatus();
      return data;
    },
    [refreshStatus]
  );

  const uploadSchema = useCallback(
    async (nextSchema) => {
      const { data } = await sdodEndpoints.uploadSchema(nextSchema);
      setSchema(data);
      await refreshStatus();
      return data;
    },
    [refreshStatus]
  );

  const generateData = useCallback(
    async (rowsPerTable) => {
      const { data } = await sdodEndpoints.generateData(rowsPerTable);
      setStatus(data);
      return data;
    },
    []
  );

  const value = {
    status,
    setStatus,
    refreshStatus,
    questions,
    setQuestions,
    answers,
    setAnswersState,
    schema,
    setSchema,
    submitIntent,
    submitAnswers,
    generateSchema,
    saveSchema,
    uploadSchema,
    generateData,
    toast,
    notify,
  };

  return <SdodContext.Provider value={value}>{children}</SdodContext.Provider>;
}

export function useSdodState() {
  const ctx = useContext(SdodContext);
  if (!ctx) throw new Error("useSdodState must be used within SdodStateProvider");
  return ctx;
}
