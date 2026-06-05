"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

import { api } from "@/lib/api";

interface BucketState {
  bucket: string;
  setBucket: (b: string) => void;
  buckets: string[];
  refresh: () => void;
  create: (name: string) => Promise<void>;
}

const Ctx = createContext<BucketState | null>(null);

export function useBucket(): BucketState {
  const c = useContext(Ctx);
  if (!c) throw new Error("useBucket must be used within BucketProvider");
  return c;
}

export function BucketProvider({ children }: { children: React.ReactNode }) {
  const [bucket, setBucketState] = useState("default");
  const [buckets, setBuckets] = useState<string[]>(["default"]);

  const refresh = useCallback(() => {
    api
      .listBuckets()
      .then((r) => setBuckets(r.buckets.length ? r.buckets : ["default"]))
      .catch(() => {});
  }, []);

  useEffect(() => {
    const saved = localStorage.getItem("adarag.bucket");
    if (saved) setBucketState(saved);
    refresh();
  }, [refresh]);

  const setBucket = useCallback((b: string) => {
    setBucketState(b);
    localStorage.setItem("adarag.bucket", b);
  }, []);

  const create = useCallback(
    async (name: string) => {
      const r = await api.createBucket(name);
      const res = await api.listBuckets();
      setBuckets(res.buckets);
      setBucket(r.bucket);
    },
    [setBucket],
  );

  return (
    <Ctx.Provider value={{ bucket, setBucket, buckets, refresh, create }}>{children}</Ctx.Provider>
  );
}
