"""
网页浏览服务（Playwright）
"""
import re
from urllib.parse import quote_plus
from app.config.settings import settings

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
except Exception:  # pragma: no cover - 运行时给出提示
    sync_playwright = None
    PlaywrightTimeoutError = Exception


class MCPBrowserClient:
    """使用 Playwright 实现的网页浏览器"""

    def __init__(self) -> None:
        self.timeout = settings.BROWSER_MCP_TIMEOUT
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
        self.max_lines = 200

    def _is_url(self, text: str) -> bool:
        return bool(re.match(r"^https?://", text.strip(), re.IGNORECASE))

    def browse(self, query_or_url: str) -> str:
        """
        浏览网页并返回文本内容

        参数:
            query_or_url: 网址或搜索关键词

        返回:
            str: 页面文本内容
        """
        query_or_url = (query_or_url or "").strip()
        if not query_or_url:
            return "浏览失败: 未提供网址或关键词"

        if not sync_playwright:
            return "浏览失败: Playwright 未安装，请先安装 playwright 并执行 `python -m playwright install`"

        if self._is_url(query_or_url):
            url = query_or_url
        else:
            url = f"https://duckduckgo.com/?q={quote_plus(query_or_url)}"

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(user_agent=self.user_agent)
                page = context.new_page()

                page.goto(url, wait_until="domcontentloaded", timeout=self.timeout * 1000)
                try:
                    page.wait_for_load_state("networkidle", timeout=self.timeout * 1000)
                except PlaywrightTimeoutError:
                    pass

                title = page.title() or "无标题"
                text = page.evaluate("document.body.innerText || ''")

                context.close()
                browser.close()

            lines = [line.strip() for line in text.splitlines() if line.strip() and len(line.strip()) > 2]
            clean_text = "\n".join(lines[: self.max_lines])

            if not clean_text:
                clean_text = "页面内容为空或无法解析"

            result_text = f"URL: {url}\n"
            result_text += f"标题: {title}\n"
            result_text += f"\n{clean_text}\n"

            if len(lines) > self.max_lines:
                result_text += f"\n... (已省略 {len(lines) - self.max_lines} 行内容)"

            return result_text

        except PlaywrightTimeoutError:
            return f"浏览失败: 页面加载超时（{self.timeout}秒）"
        except Exception as e:
            return f"浏览失败: {str(e)}"


mcp_browser_client = MCPBrowserClient()
