"""
简单的网页浏览服务
使用 curl + html.parser 获取网页内容
"""
import re
import subprocess
import html.parser
from urllib.parse import quote_plus
from app.config.settings import settings


class TextExtractor(html.parser.HTMLParser):
    """从HTML中提取文本内容的解析器"""

    def __init__(self):
        super().__init__()
        self.text = []
        self.skip_tags = {'script', 'style', 'noscript', 'head', 'meta', 'link', 'img', 'svg'}
        self.skip_content = False

    def handle_starttag(self, tag, attrs):
        if tag in self.skip_tags:
            self.skip_content = True

    def handle_endtag(self, tag):
        if tag in self.skip_tags:
            self.skip_content = False

    def handle_data(self, data):
        if not self.skip_content and data.strip():
            self.text.append(data)

    def get_text(self):
        return '\n'.join(self.text)


class MCPBrowserClient:
    """使用 curl 实现的网页浏览器"""

    def __init__(self) -> None:
        self.timeout = settings.BROWSER_MCP_TIMEOUT
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

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

        if self._is_url(query_or_url):
            url = query_or_url
        else:
            url = f"https://duckduckgo.com/?q={quote_plus(query_or_url)}"

        try:
            # 使用 curl 获取页面内容
            cmd = [
                'curl', '-s',
                '--connect-timeout', str(self.timeout),
                '-H', f'User-Agent: {self.headers["User-Agent"]}',
                url
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            if result.returncode != 0:
                return f"浏览失败: curl执行失败 (退出码: {result.returncode})\n错误: {result.stderr}"

            html_content = result.stdout

            # 提取标题
            title_match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)
            title = title_match.group(1).strip() if title_match else "无标题"

            # 提取文本内容
            extractor = TextExtractor()
            extractor.feed(html_content)
            text = extractor.get_text()

            # 清理空白行
            lines = [line.strip() for line in text.split('\n') if line.strip() and len(line.strip()) > 3]
            clean_text = '\n'.join(lines[:200])  # 限制行数

            if not clean_text:
                clean_text = "页面内容为空或无法解析"

            # 尝试获取HTTP状态码
            status_code = "未知"
            if result.stderr:
                status_match = re.search(r'HTTP/[\d.]+\s+(\d+)', result.stderr)
                if status_match:
                    status_code = status_match.group(1)

            result_text = f"URL: {url}\n"
            result_text += f"标题: {title}\n"
            result_text += f"状态码: {status_code}\n"
            result_text += f"\n{clean_text}\n"

            # 如果内容被截断，添加提示
            if len(lines) > 200:
                result_text += f"\n... (已省略 {len(lines) - 200} 行内容)"

            return result_text

        except subprocess.TimeoutExpired:
            return f"浏览失败: 页面加载超时（{self.timeout}秒）"
        except FileNotFoundError:
            return "浏览失败: curl命令未找到，请确保系统已安装curl"
        except Exception as e:
            return f"浏览失败: {str(e)}"


mcp_browser_client = MCPBrowserClient()
