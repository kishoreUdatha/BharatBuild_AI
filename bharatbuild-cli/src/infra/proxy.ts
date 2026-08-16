import https from "https";
import http from "http";

export function getProxyConfig(): { httpProxy?: string; httpsProxy?: string; noProxy?: string } {
  return {
    httpProxy: process.env["HTTP_PROXY"] ?? process.env["http_proxy"],
    httpsProxy: process.env["HTTPS_PROXY"] ?? process.env["https_proxy"],
    noProxy: process.env["NO_PROXY"] ?? process.env["no_proxy"],
  };
}

export function isProxyRequired(url: string): boolean {
  const { noProxy } = getProxyConfig();
  if (!noProxy) return true;
  const hostname = new URL(url).hostname;
  return !noProxy.split(",").some((pat) => hostname === pat.trim() || hostname.endsWith("." + pat.trim()));
}

export function applyProxyToFetch(): void {
  const { httpsProxy } = getProxyConfig();
  if (!httpsProxy) return;
  process.env["HTTPS_PROXY"] = httpsProxy;
  process.env["HTTP_PROXY"] = process.env["HTTP_PROXY"] ?? httpsProxy;
}
