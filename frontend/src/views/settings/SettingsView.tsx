import { useEffect, useState } from "react";
import { systemApi } from "@/services/api/system";
import { infraApi, type InfraNode } from "@/services/api/infra";

type TierKey = "device" | "edge" | "cloud";

type NodeConfig = {
  enabled: boolean;
  label: string;
  baseUrl: string;
  provider: string;
  model: string;
  capabilities: string;
  apiPath: string;
  healthPath: string;
  apiKeyHeader: string;
};

const DEFAULT_CONFIG: Record<TierKey, NodeConfig> = {
  device: {
    enabled: true,
    label: "本机终端",
    baseUrl: "http://localhost:11434",
    provider: "ollama",
    model: "ark-code-latest",
    capabilities: "chat",
    apiPath: "/api/generate",
    healthPath: "/api/tags",
    apiKeyHeader: "Authorization",
  },
  edge: {
    enabled: false,
    label: "区域边缘节点",
    baseUrl: "http://localhost:8900",
    provider: "aegis_edge",
    model: "ark-code-latest",
    capabilities: "chat, reasoning",
    apiPath: "/infer",
    healthPath: "/health",
    apiKeyHeader: "Authorization",
  },
  cloud: {
    enabled: false,
    label: "云端推理服务",
    baseUrl: "https://api.openai.com/v1",
    provider: "openai_api",
    model: "ark-code-latest",
    capabilities: "chat, reasoning, long_context",
    apiPath: "/chat/completions",
    healthPath: "/models",
    apiKeyHeader: "Authorization",
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
    if (saved) {
      // 深合并：旧 localStorage 里可能缺新字段或 provider 被改过，
      // 保证云侧卡片默认仍是 openai_api，API Key 输入框必定出现。
      const raw = JSON.parse(saved);
      const merged = { ...DEFAULT_CONFIG };
      for (const tier of Object.keys(DEFAULT_CONFIG) as TierKey[]) {
        merged[tier] = { ...DEFAULT_CONFIG[tier], ...(raw[tier] || {}) };
      }
      return merged;
    }
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
  const [backendNodes, setBackendNodes] = useState<InfraNode[]>([]);

  useEffect(() => {
    setConfig(loadConfig());
    systemApi
      .getMode()
      .then((m) => setHasKey(m.has_key))
      .catch(() => setHasKey(null));
    infraApi.listNodes().then(setBackendNodes).catch(() => setBackendNodes([]));
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

  const saveConfig = async () => {
    const nodes = (Object.keys(config) as TierKey[]).map((tier) => {
      const node = config[tier];
      return {
        node_id: `${tier}_local`,
        tier,
        base_url: node.baseUrl,
        provider: node.provider,
        model_id: node.model,
        capabilities: node.capabilities.split(",").map((value) => value.trim()).filter(Boolean),
        api_path: node.apiPath,
        health_path: node.healthPath,
        api_key_header: node.apiKeyHeader,
        request_format: node.provider === "anthropic" ? "anthropic" : node.provider === "custom" ? "json" : "openai",
        enabled: node.enabled,
      };
    });
    localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
    try {
      setBackendNodes(await infraApi.configureNodes(nodes));
      setSaved(true);
    } catch (err) {
      setSaved(false);
      setCloudKeyMsg(err instanceof Error ? `配置同步失败：${err.message}` : "配置同步失败");
    }
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
          <span className="eyebrow">RUNTIME CONTROL / PROVIDER ROUTING</span>
          <h2 className="settings-hero__title">运行配置</h2>
          <p className="settings-hero__desc">
            为每个端、边、云节点配置协议、连接、模型和健康检查。
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
          <button type="button" className="settings-button settings-button--primary" onClick={() => void saveConfig()}>
            {saved ? "已保存" : "保存配置"}
          </button>
        </div>
      </div>

      <div className="settings-grid">
        {(Object.keys(TIER_META) as TierKey[]).map((tier) => {
          const meta = TIER_META[tier];
          const node = config[tier];
          const backendNode = backendNodes.find((candidate) => candidate.tier === tier);
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
                    <option value="openai_api">OpenAI 兼容</option>
                    <option value="openai">OpenAI</option>
                    <option value="anthropic">Anthropic</option>
                    <option value="custom">自定义 JSON</option>
                  </select>
                </label>
                <label>
                  <span>模型标识</span>
                  <input value={node.model} onChange={(event) => updateNode(tier, { model: event.target.value })} />
                </label>
                <label>
                  <span>请求路径</span>
                  <input value={node.apiPath} onChange={(event) => updateNode(tier, { apiPath: event.target.value })} />
                </label>
                <label>
                  <span>探活路径</span>
                  <input value={node.healthPath} onChange={(event) => updateNode(tier, { healthPath: event.target.value })} />
                </label>
                <label>
                  <span>认证 Header</span>
                  <input value={node.apiKeyHeader} onChange={(event) => updateNode(tier, { apiKeyHeader: event.target.value })} />
                </label>
                <label className="node-config__field--wide">
                  <span>能力标签</span>
                  <input value={node.capabilities} onChange={(event) => updateNode(tier, { capabilities: event.target.value })} />
                </label>
              </div>

              {/* 云侧节点：API Key 输入框（端/边暂不单独配置，统一走云 API） */}
              {["openai_api", "openai", "anthropic", "custom"].includes(node.provider) ? (
                <div className="node-config__apikey">
                  <div className="node-config__apikey-head">
                    <span>{node.provider === "anthropic" ? "Anthropic API Key" : "API Key（可选）"}</span>
                    <span className={`badge badge--${hasKey ? "succeeded" : "cancelled"}`}>
                      {hasKey === null ? "查询中…" : hasKey ? "已配置" : "未配置"}
                    </span>
                  </div>
                  <div className="node-config__apikey-row">
                    <input
                      type="password"
                      placeholder={hasKey ? "已配置 Key，输入新 Key 可覆盖" : "sk-…（输入后同步到后端）"}
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
                <span className={`node-config__dot${backendNode?.status === "online" ? " node-config__dot--on" : ""}`} />
                <span>
                  {!node.enabled ? "已停用" : backendNode?.status === "online" ? "后端在线" : backendNode?.status === "offline" ? "后端离线" : "等待探活"}
                </span>
                {backendNode ? <small>{backendNode.model_id} · 失败 {backendNode.consecutive_failures} 次</small> : null}
                <code>{tier}</code>
              </footer>
            </article>
          );
        })}
      </div>

      <div className="settings-note">
        <span className="settings-note__mark">i</span>
        <p>
          任一层卡片选择 <code>OpenAI API</code> 时会出现 <code>API Key</code> 输入框；Key 全局共享，
          输入后点「同步到后端」即写入 <code>tooling/configs/.env</code> 并即时生效。自部署 Ollama
          走 URL 直连（<code>http://&lt;IP&gt;:11434/v1</code>），默认无需 Key。节点其余配置仅保存在当前浏览器，用于本地演示。
        </p>
      </div>
    </section>
  );
}
