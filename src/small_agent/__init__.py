"""Small Agent 教学项目。"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("small-agent")
except PackageNotFoundError:  # 允许直接从未安装的源码树导入。
    __version__ = "0+unknown"
