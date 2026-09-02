import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Save, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";

import { api } from "../api";
import { useToast } from "../components/Toast";
import { Button, Field, Spinner, inputClass } from "../components/ui";
import type { Profile } from "../types";

export default function ProfilePage() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const { data: profile, isLoading } = useQuery({ queryKey: ["profile"], queryFn: api.profile.get });

  const [form, setForm] = useState<Partial<Profile> | null>(null);
  useEffect(() => {
    if (profile && form === null) {
      setForm({ ...profile, skills: profile.skills });
    }
  }, [profile, form]);

  const save = useMutation({
    mutationFn: (payload: Partial<Profile>) => api.profile.update(payload),
    onSuccess: () => {
      toast("Profile saved — every future draft uses it");
      void queryClient.invalidateQueries({ queryKey: ["profile"] });
    },
  });

  if (isLoading || !form) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner />
      </div>
    );
  }

  const set = <K extends keyof Profile>(key: K, value: Profile[K]) =>
    setForm((current) => ({ ...current, [key]: value }));

  return (
    <div className="animate-rise mx-auto max-w-2xl px-6 py-6">
      <header className="mb-5">
        <h1 className="font-display text-xl font-bold tracking-tight">Profile & voice</h1>
        <p className="text-[13px] text-ink-2">
          This is the grounding context for every cover letter and follow-up Gemini writes for you — alongside
          your own past drafts, so the words sound like you.
        </p>
      </header>

      <form
        className="ring-card space-y-4 rounded-2xl bg-card p-6"
        onSubmit={(event) => {
          event.preventDefault();
          save.mutate(form);
        }}
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Full name">
            <input className={inputClass} value={form.name ?? ""} onChange={(e) => set("name", e.target.value)} />
          </Field>
          <Field label="Years of experience">
            <input
              className={inputClass}
              type="number"
              min={0}
              step={0.5}
              value={form.years_experience ?? 0}
              onChange={(e) => set("years_experience", Number(e.target.value))}
            />
          </Field>
        </div>
        <Field label="Headline">
          <input
            className={inputClass}
            placeholder="Backend engineer — Python, distributed systems"
            value={form.headline ?? ""}
            onChange={(e) => set("headline", e.target.value)}
          />
        </Field>
        <Field label="Skills (comma separated)">
          <input
            className={inputClass}
            placeholder="Python, FastAPI, PostgreSQL, GCP"
            value={(form.skills ?? []).join(", ")}
            onChange={(e) =>
              set(
                "skills",
                e.target.value
                  .split(",")
                  .map((skill) => skill.trim())
                  .filter(Boolean),
              )
            }
          />
        </Field>
        <Field label="Proof points — achievements with numbers">
          <textarea
            className={`${inputClass} min-h-24 resize-y`}
            placeholder="Cut p95 latency 40%; led a 3-engineer pod shipping a service that processes 2M events/day"
            value={form.achievements ?? ""}
            onChange={(e) => set("achievements", e.target.value)}
          />
        </Field>
        <Field label="Preferred tone">
          <input className={inputClass} value={form.tone ?? ""} onChange={(e) => set("tone", e.target.value)} />
        </Field>

        <div className="flex items-center justify-between pt-2">
          <p className="flex items-center gap-1.5 text-[11px] text-ink-3">
            <Sparkles size={12} className="text-accent" />
            Facts only — Gemini is instructed never to invent achievements.
          </p>
          <Button type="submit" variant="primary" disabled={save.isPending}>
            {save.isPending ? <Spinner className="border-on-accent/30 border-t-on-accent" /> : <Save size={15} />}
            Save profile
          </Button>
        </div>
      </form>
    </div>
  );
}
