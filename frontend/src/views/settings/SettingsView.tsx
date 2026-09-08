import { useEffect, useState } from "react";
import { systemApi } from "@/services/api/system";

type TierKey = "device" | "edge" | "cloud";

type NodeConfig = {
  enabled: boolean;
  label: string;
  baseUrl: string;
  provider: string;
  model: string;
  capabilities: string;
};

const DEFAULT_CONFIG: Record<TierKey, NodeConfig> = {
  device: {
    enabled: true,
    label: "本机终端",
    baseUrl: "http://localhost:11434",
    provider: "ollama",
    model: "qwen2.5:0.5b",
    capabilities: "chat",
  },
  edge: {
    enabled: false,
    label: "区域边缘节点",
    baseUrl: "http://localhost:8900",
    provider: "aegis_edge",
    model: "qwen2.5:7b",
    capabilities: "chat, reasoning",
  },
  cloud: {
    enabled: false,
    label: "云端推理服务",
    baseUrl: "https://api.openai.com/v1",
    provider: "openai_api",
    model: "gpt-4o-mini",
    capabilities: "chat, reasoning, long_context",
  },
};

const TIER_META: Record<TierKey, { index: string; title: string; subtitle: string }> = {
  device: { index: "01", title: "端侧", subtitle: "隐私数据留在本机" },
  edge: { index: "02", title: "边侧", subtitle: "区域内聚合与中型模型" },
  cloud: { index: "03", title: "云侧", subtitle: "复杂任务与长上下文" },
};

const STORAGE_KEY = "aegisos-node-config";

function loadConfig(): Record<TierKey, NodeConfig> {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) return { ...DEFAULT_CONFIG, ...JSON.parse(saved) };
  } catch {
    // Invalid local state falls back to the demo defaults.
  }
  return DEFAULT_CONFIG;
}

export function SettingsView() {
  const [config, setConfig] = useState<Record<TierKey, NodeConfig>>(DEFAULT_CONFIG);
  const [saved, setSaved] = useState(false);
  const [cloudApiKey, setCloudApiKey] = useState("");
  const [hasKey, setHasKey] = useState<boolean | null>(null);
  const [cloudKeySaving, setCloudKeySaving] = useState(false);
  const [cloudKeyMsg, setCloudKeyMsg] = useState<string | null>(null);

  useEffect(() => {
    setConfig(loadConfig());
    systemApi
      .getMode()
      .then((m) => setHasKey(m.has_key))
      .catch(() => setHasKey(null));
  }, []);

  const saveCloudApiKey = async () => {
    const key = cloudApiKey.trim();
    if (!key || cloudKeySaving) return;
    setCloudKeySaving(true);
    setCloudKeyMsg(null);
    try {
      const m = await systemApi.setApiKey(key);
      setHasKey(m.has_key);
      setCloudApiKey("");
      setCloudKeyMsg(
        m.has_key
          ? "✓ 已同步到后端（tooling/configs/.env），真实 LLM 模式可直接使用"
          : "保存完成，但后端未识别到 Key，请检查。",
      );
    } catch (err) {
      setCloudKeyMsg(err instanceof Error ? `保存失败：${err.message}` : "保存失败");
    } finally {
      setCloudKeySaving(false);
    }
  };

  const updateNode = (tier: TierKey, patch: Partial<NodeConfig>) => {
    setConfig((current) => ({
      ...current,
      [tier]: { ...current[tier], ...patch },
    }));
    setSaved(false);
  };

  const saveConfig = () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
    setSaved(true);
  };

  const resetConfig = () => {
    setConfig(DEFAULT_CONFIG);
    localStorage.removeItem(STORAGE_KEY);
    setSaved(false);
  };

  return (
    <section className="view settings-view">
      <header className="settings-hero">
        <div>
          <span className="eyebrow">RUNTIME CONTROL / LOCAL DEMO</span>
          <h2 className="settings-hero__title">运行配置</h2>
          <p className="settings-hero__desc">
            配置推理落点、模型和能力标签。修改仅保存在当前浏览器，用于本地演示。
          </p>
        </div>
        <div className="settings-hero__status">
          <span className="settings-hero__pulse" />
          <span>{Object.values(config).filter((node) => node.enabled).length} 个节点启用</span>
        </div>
      </header>

      {/* 云侧 LLM API Key：前端配置 → 同步后端（写入 .env + 即时生效） */}
      <div className="settings-actions">
        <span className="settings-actions__hint">端 → 边 → 云，按任务隐私与复杂度选择</span>
        <div className="settings-actions__buttons">
          <button type="button" className="settings-button settings-button--quiet" onClick={resetConfig}>
            恢复默认
          </button>
          <button type="button" className="settings-button settings-button--primary" onClick={saveConfig}>
            {saved ? "已保存" : "保存配置"}
          </button>
        </div>
      </div>

      <div className="settings-grid">
        {(Object.keys(TIER_META) as TierKey[]).map((tier) => {
          const meta = TIER_META[tier];
          const node = config[tier];
          return (
            <article className={`node-config node-config--${tier}`} key={tier}>
              <div className="node-config__header">
                <div className="node-config__identity">
                  <span className="node-config__index">{meta.index}</span>
                  <div>
                    <h3>{meta.title}</h3>
                    <p>{meta.subtitle}</p>
                  </div>
                </div>
                <label className="switch" title={`${meta.title}启用状态`}>
                  <input
                    type="checkbox"
                    checked={node.enabled}
                    onChange={(event) => updateNode(tier, { enabled: event.target.checked })}
                  />
                  <span className="switch__track" />
                </label>
              </div>

              <div className="node-config__fields">
                <label>
                  <span>显示名称</span>
                  <input value={node.label} onChange={(event) => updateNode(tier, { label: event.target.value })} />
                </label>
                <label className="node-config__field--wide">
                  <span>服务地址</span>
                  <input value={node.baseUrl} onChange={(event) => updateNode(tier, { baseUrl: event.target.value })} />
                </label>
                <label>
                  <span>Provider</span>
                  <select value={node.provider} onChange={(event) => updateNode(tier, { provider: event.target.value })}>
                    <option value="ollama">Ollama</option>
                    <option value="aegis_edge">Aegis Edge</option>
                    <option value="openai_api">OpenAI API</option>
                  </select>
                </label>
                <label>
                  <span>模型标识</span>
                  <input value={node.model} onChange={(event) => updateNode(tier, { model: event.target.value })} />
                </label>
                <label className="node-config__field--wide">
                  <span>能力标签</span>
                  <input value={node.capabilities} onChange={(event) => updateNode(tier, { capabilities: event.target.value })} />
                </label>
              </div>

              {/* 云侧节点：Provider 选 OpenAI API 时出现 API Key 输入框，同步到后端 */}
              {tier === "cloud" && node.provider === "openai_api" ? (
                <div className="node-config__apikey">
                  <div className="node-config__apikey-head">
                    <span>OpenAI API Key</span>
                    <span className={`badge badge--${hasKey ? "succeeded" : "cancelled"}`}>
                      {hasKey === null ? "查询中…" : hasKey ? "已配置" : "未配置"}
                    </span>
                  </div>
                  <div className="node-config__apikey-row">
                    <input
                      type="password"
                      placeholder={hasKey ? "已配置 Key，输入新 Key 可覆盖" : "sk-…"}
                      value={cloudApiKey}
                      onChange={(e) => setCloudApiKey(e.target.value)}
                      aria-label="OpenAI API Key"
                    />
                    <button
                      type="button"
                      className="settings-button settings-button--primary"
                      onClick={() => void saveCloudApiKey()}
                      disabled={cloudKeySaving || !cloudApiKey.trim()}
                    >
                      {cloudKeySaving ? "同步中…" : "同步到后端"}
                    </button>
                  </div>
                  {cloudKeyMsg ? <p className="node-config__apikey-msg">{cloudKeyMsg}</p> : null}
                </div>
              ) : null}

              <footer className="node-config__footer">
                <span className={`node-config__dot${node.enabled ? " node-config__dot--on" : ""}`} />
                <span>{node.enabled ? "参与任务调度" : "已停用"}</span>
                <code>{tier}</code>
              </footer>
            </article>
          );
        })}
      </div>

      <div className="settings-note">
        <span className="settings-note__mark">i</span>
        <p>
          云侧节点 Provider 选 <code>OpenAI API</code> 时，会就地出现
          <code> API Key</code> 输入框，保存后同步到后端（
          <code>tooling/configs/.env</code>，15 秒内热生效），真实 LLM 模式直接可用。
          端侧/边侧暂不单独配置，统一走云 API；节点其余配置仅保存在当前浏览器，用于本地演示。
        </p>
      </div>
    </section>
  );
}
