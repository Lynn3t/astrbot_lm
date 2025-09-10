from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import httpx
import json

@register("spotify_now_playing", "Fimall", "获取Spotify当前播放状态插件", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
    
    @filter.command("lm")
    async def get_now_playing(self, event: AstrMessageEvent):
        """获取Spotify当前播放状态"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get("https://spotify.fimall.filegear-sg.me/get")
                response.raise_for_status()
                
                data = response.json()
                title = data.get("title", "未知曲目")
                artist = data.get("artist", "未知艺术家")
                album_art_url = data.get("album_art_url", "")
                
                # 发送文本消息
                yield event.plain_result(f"正在播放 | {title} - {artist}")
                
                # 发送专辑封面图片
                if album_art_url:
                    yield event.image_result(album_art_url)
                    
        except httpx.TimeoutException:
            logger.error("获取Spotify状态超时")
            yield event.plain_result("获取播放状态超时，请稍后再试")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP错误: {e.response.status_code}")
            yield event.plain_result("获取播放状态失败，请检查服务状态")
        except json.JSONDecodeError:
            logger.error("JSON解析失败")
            yield event.plain_result("数据解析失败，请联系管理员")
        except Exception as e:
            logger.error(f"获取播放状态时发生错误: {str(e)}")
            yield event.plain_result("获取播放状态时发生未知错误")

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
