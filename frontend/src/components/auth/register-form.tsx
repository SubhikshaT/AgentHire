"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, Briefcase, Loader2, UserRound } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";

import { FormField } from "@/components/auth/form-field";
import { PasswordInput } from "@/components/auth/password-input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { homePathFor, useRegister } from "@/hooks/use-auth";
import { ApiError, errorMessage } from "@/lib/api";
import { cn } from "@/lib/utils";

const schema = z
  .object({
    role: z.enum(["recruiter", "candidate"], {
      message: "Choose how you will use AgentHire",
    }),
    name: z.string().trim().min(2, "Enter your full name").max(120),
    email: z.email("Enter a valid email address"),
    password: z.string().min(8, "Use at least 8 characters").max(128),
    confirm: z.string(),
  })
  .refine((v) => v.password === v.confirm, {
    path: ["confirm"],
    message: "Passwords do not match",
  });
type Values = z.infer<typeof schema>;

const roles = [
  {
    value: "recruiter",
    label: "Recruiter",
    text: "Post jobs, screen resumes, run interviews",
    icon: Briefcase,
  },
  {
    value: "candidate",
    label: "Candidate",
    text: "Apply to jobs, practice interviews",
    icon: UserRound,
  },
] as const;

export function RegisterForm() {
  const router = useRouter();
  const params = useSearchParams();
  const signup = useRegister();
  const initialRole = params.get("role");
  const {
    register,
    control,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      role:
        initialRole === "recruiter" || initialRole === "candidate"
          ? initialRole
          : undefined,
    },
  });

  const onSubmit = handleSubmit((values) =>
    signup.mutate(
      {
        role: values.role,
        name: values.name,
        email: values.email,
        password: values.password,
      },
      {
        onSuccess: (user) => router.replace(homePathFor(user.role)),
        onError: (err) => {
          if (err instanceof ApiError && err.code === "email_taken") {
            setError("email", { message: err.message });
          }
        },
      },
    ),
  );

  const showBanner =
    signup.isError &&
    !(signup.error instanceof ApiError && signup.error.code === "email_taken");

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">
          Create your account
        </h1>
        <p className="text-muted-foreground mt-1 text-sm">
          It takes less than a minute.
        </p>
      </div>

      {showBanner && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{errorMessage(signup.error)}</AlertDescription>
        </Alert>
      )}

      <fieldset>
        <legend className="mb-2 text-sm font-medium">I am a</legend>
        <Controller
          control={control}
          name="role"
          render={({ field }) => (
            <div
              role="radiogroup"
              aria-invalid={!!errors.role}
              className="grid grid-cols-2 gap-3"
            >
              {roles.map(({ value, label, text, icon: Icon }) => {
                const checked = field.value === value;
                return (
                  <label
                    key={value}
                    className={cn(
                      "has-[:focus-visible]:ring-ring flex cursor-pointer flex-col gap-1.5 rounded-xl border p-3 text-sm transition-colors has-[:focus-visible]:ring-2",
                      checked
                        ? "border-ring bg-secondary/70"
                        : "hover:bg-muted",
                    )}
                  >
                    <input
                      type="radio"
                      name={field.name}
                      value={value}
                      checked={checked}
                      onChange={() => field.onChange(value)}
                      onBlur={field.onBlur}
                      className="sr-only"
                    />
                    <Icon
                      className={cn(
                        "size-5",
                        checked
                          ? "text-secondary-foreground"
                          : "text-muted-foreground",
                      )}
                    />
                    <span className="font-medium">{label}</span>
                    <span className="text-muted-foreground text-xs leading-snug">
                      {text}
                    </span>
                  </label>
                );
              })}
            </div>
          )}
        />
        {errors.role && (
          <p role="alert" className="text-destructive mt-1.5 text-sm">
            {errors.role.message}
          </p>
        )}
      </fieldset>

      <FormField id="name" label="Full name" error={errors.name?.message}>
        <Input
          id="name"
          autoComplete="name"
          className="h-10"
          aria-invalid={!!errors.name}
          {...register("name")}
        />
      </FormField>

      <FormField id="email" label="Email" error={errors.email?.message}>
        <Input
          id="email"
          type="email"
          autoComplete="email"
          className="h-10"
          aria-invalid={!!errors.email}
          {...register("email")}
        />
      </FormField>

      <FormField
        id="password"
        label="Password"
        error={errors.password?.message}
        hint="At least 8 characters."
      >
        <PasswordInput
          id="password"
          autoComplete="new-password"
          aria-invalid={!!errors.password}
          {...register("password")}
        />
      </FormField>

      <FormField
        id="confirm"
        label="Confirm password"
        error={errors.confirm?.message}
      >
        <PasswordInput
          id="confirm"
          autoComplete="new-password"
          aria-invalid={!!errors.confirm}
          {...register("confirm")}
        />
      </FormField>

      <Button
        type="submit"
        size="lg"
        className="h-10 w-full"
        disabled={signup.isPending}
      >
        {signup.isPending && <Loader2 className="animate-spin" />}
        Create account
      </Button>

      <p className="text-muted-foreground text-center text-sm">
        Already have an account?{" "}
        <Link
          href="/login"
          className="text-primary font-medium underline-offset-4 hover:underline"
        >
          Log in
        </Link>
      </p>
    </form>
  );
}
