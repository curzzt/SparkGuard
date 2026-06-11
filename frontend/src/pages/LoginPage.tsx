import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { login, register } from "@/api/auth";
import SparkBackground from "@/components/layout/SparkBackground";
import Button from "@/components/ui/Button";
import { cn } from "@/components/ui/cn";
import { Field, Input } from "@/components/ui/Input";
import { FullScreenSpinner } from "@/components/ui/Spinner";
import { useAuth } from "@/hooks/useAuth";
import { isDevAuthBypassEnabled } from "@/store/authStore";

type Tab = "login" | "register";

interface FormErrors {
  phone?: string;
  password?: string;
  passwordConfirm?: string;
  submit?: string;
}

function BrandOrbit() {
  return (
    <div className="relative mx-auto h-56 w-56 lg:h-72 lg:w-72" aria-hidden>
      <svg viewBox="0 0 200 200" className="h-full w-full">
        <g className="orbit-ring-slow" style={{ transformBox: "fill-box" }}>
          <circle cx="100" cy="100" r="92" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="1" strokeDasharray="3 7" />
          <circle cx="100" cy="8" r="3" fill="#22d3ee">
            <animate attributeName="opacity" values="1;0.4;1" dur="2s" repeatCount="indefinite" />
          </circle>
        </g>
        <g className="orbit-ring" style={{ transformBox: "fill-box" }}>
          <circle cx="100" cy="100" r="66" fill="none" stroke="rgba(255,107,53,0.25)" strokeWidth="1" />
          <circle cx="166" cy="100" r="3.5" fill="#ff6b35">
            <animate attributeName="opacity" values="1;0.5;1" dur="1.6s" repeatCount="indefinite" />
          </circle>
        </g>
        <circle cx="100" cy="100" r="40" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="1" />
        <path
          d="M100 72c5 11 18 16 18 31a18 18 0 1 1-36 0c0-8 4-12 8-17 1 5 4 8 6 9-1-9 0-16 4-23z"
          fill="rgba(255,107,53,0.15)"
          stroke="#ff6b35"
          strokeWidth="2"
          strokeLinejoin="round"
        >
          <animate attributeName="stroke" values="#ff6b35;#ffb347;#ff6b35" dur="3s" repeatCount="indefinite" />
        </path>
      </svg>
      <div className="absolute inset-0 -z-10 rounded-full bg-spark/10 blur-3xl" />
    </div>
  );
}

export default function LoginPage() {
  const navigate = useNavigate();
  const { setAuth, accessToken, hasHydrated } = useAuth();
  const [tab, setTab] = useState<Tab>("login");
  const [loading, setLoading] = useState(false);
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [errors, setErrors] = useState<FormErrors>({});

  useEffect(() => {
    document.title = "登录 - 火花续航";
  }, []);

  useEffect(() => {
    if (isDevAuthBypassEnabled()) {
      navigate("/", { replace: true });
      return;
    }
    if (hasHydrated && accessToken) {
      navigate("/", { replace: true });
    }
  }, [accessToken, hasHydrated, navigate]);

  const switchTab = (next: Tab) => {
    setTab(next);
    setErrors({});
  };

  const validate = (): boolean => {
    const next: FormErrors = {};
    if (!phone.trim()) {
      next.phone = "请输入手机号";
    }
    if (!password) {
      next.password = tab === "register" ? "至少 8 位，需包含字母和数字" : "请输入密码";
    } else if (tab === "register" && !/^(?=.*[A-Za-z])(?=.*\d).{8,}$/.test(password)) {
      next.password = "至少 8 位，需包含字母和数字";
    }
    if (tab === "register") {
      if (!passwordConfirm) {
        next.passwordConfirm = "请确认密码";
      } else if (passwordConfirm !== password) {
        next.passwordConfirm = "两次密码不一致";
      }
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    setLoading(true);
    setErrors({});
    try {
      const data =
        tab === "login"
          ? await login(phone.trim(), password)
          : await register(phone.trim(), password, passwordConfirm);
      setAuth(data.access_token, data.user);
      navigate("/");
    } catch (err) {
      setErrors({ submit: err instanceof Error ? err.message : tab === "login" ? "登录失败" : "注册失败" });
    } finally {
      setLoading(false);
    }
  };

  if (!hasHydrated && !isDevAuthBypassEnabled()) {
    return (
      <div className="bg-noise relative min-h-screen">
        <SparkBackground />
        <FullScreenSpinner />
      </div>
    );
  }

  return (
    <div className="bg-noise relative min-h-screen">
      <SparkBackground />
      <div className="relative z-10 mx-auto flex min-h-screen w-full max-w-[1080px] flex-col items-center justify-center gap-10 px-6 py-12 lg:flex-row lg:gap-16">
        <div className="rise-in flex flex-1 flex-col items-center gap-6 text-center lg:items-start lg:text-left">
          <div className="flex items-center gap-3">
            <span className="spark-dot" aria-hidden />
            <span className="font-hud text-[11px] uppercase tracking-[0.4em] text-ink-dim">SparkGuard</span>
          </div>
          <h1 className="brand-gradient m-0 text-4xl font-extrabold tracking-wide lg:text-5xl">火花续航</h1>
          <p className="m-0 max-w-md text-sm leading-relaxed text-ink-mid">
            到点自动续火花，结果全程可追踪。官方接口不支持的场景如实标记，绝不伪造成功。
          </p>
          <BrandOrbit />
        </div>

        <div className="rise-in w-full max-w-md flex-1" style={{ animationDelay: "0.12s" }}>
          <div className="glass glass-flow hud-corners p-7">
            <div className="mb-6 flex rounded-ctl border border-line bg-white/[0.03] p-1">
              {(["login", "register"] as const).map((key) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => switchTab(key)}
                  className={cn(
                    "flex-1 cursor-pointer rounded-lg border-none py-2 text-sm font-medium transition-all duration-150 ease-hud",
                    tab === key
                      ? "bg-gradient-to-r from-spark/90 to-flare/80 text-white shadow-glow-spark"
                      : "bg-transparent text-ink-dim hover:text-ink"
                  )}
                >
                  {key === "login" ? "登录" : "注册"}
                </button>
              ))}
            </div>

            <form onSubmit={(e) => void handleSubmit(e)} className="flex flex-col gap-4" noValidate>
              <Field label="手机号" error={errors.phone}>
                <Input
                  type="tel"
                  autoComplete="tel"
                  placeholder="13800138000"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className="font-hud"
                />
              </Field>

              <Field label="密码" error={errors.password}>
                <Input
                  type="password"
                  autoComplete={tab === "login" ? "current-password" : "new-password"}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </Field>

              {tab === "register" && (
                <Field label="确认密码" error={errors.passwordConfirm}>
                  <Input
                    type="password"
                    autoComplete="new-password"
                    placeholder="••••••••"
                    value={passwordConfirm}
                    onChange={(e) => setPasswordConfirm(e.target.value)}
                  />
                </Field>
              )}

              {errors.submit && (
                <p className="m-0 rounded-ctl border border-flare/40 bg-flare/10 px-3.5 py-2.5 text-xs text-flare">
                  {errors.submit}
                </p>
              )}

              <Button type="submit" variant="primary" size="lg" block loading={loading} className="mt-1">
                {tab === "login" ? "进入控制台" : "创建账号"}
              </Button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
