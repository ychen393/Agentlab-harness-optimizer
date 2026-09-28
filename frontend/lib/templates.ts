import type { Language } from "../types/contracts";

export type ScenarioTemplateId = "promo" | "product" | "order" | "returns" | "custom";

export interface ScenarioTemplate {
  id: ScenarioTemplateId;
  requests: Record<Language, string>;
  scenarioId: string | null;
}

export const SCENARIO_TEMPLATES: Record<ScenarioTemplateId, ScenarioTemplate> = {
  promo: {
    id: "promo",
    requests: {
      zh: "我的订单于 2026-02-10 支付，金额为 650 元。请问适用哪个促销活动？我是否符合赠品领取条件？",
      en: "My order was paid on 2026-02-10 for 650 RMB. Which promotion applies, and do I qualify for the gift?",
    },
    scenarioId: "CS6",
  },
  product: {
    id: "product",
    requests: { zh: "请查找跑鞋，并展示可购买的商品。", en: "Find running shoes and show the available products." },
    scenarioId: null,
  },
  order: {
    id: "order",
    requests: { zh: "我的订单目前是什么状态？预计何时送达？", en: "What is the status of my order and when will it be delivered?" },
    scenarioId: null,
  },
  returns: {
    id: "returns",
    requests: { zh: "线上订单的退货政策是什么？", en: "What is the return policy for an online order?" },
    scenarioId: null,
  },
  custom: { id: "custom", requests: { zh: "", en: "" }, scenarioId: null },
};

export function requestForTemplate(id: ScenarioTemplateId, language: Language): string {
  return SCENARIO_TEMPLATES[id].requests[language];
}
