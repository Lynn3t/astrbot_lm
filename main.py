from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import httpx
import json
import random
import re

@register("spotify_now_playing", "Fimall", "获取Spotify当前播放状态插件", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
    
    @filter.command("lm")
    async def handle_lm_command(self, event: AstrMessageEvent):
        """处理LM音乐相关命令"""
        command_parts = event.message_plain.strip().split()
        
        # 如果只有 /lm，显示当前播放
        if len(command_parts) == 1:
            async for result in self.get_now_playing(event):
                yield result
            return
            
        subcommand = command_parts[1].lower()
        
        if subcommand == "list":
            # 处理 list 命令
            count = 5  # 默认值
            if len(command_parts) > 2:
                try:
                    count = int(command_parts[2])
                    count = max(1, min(50, count))  # 限制在1-50之间
                except ValueError:
                    yield event.plain_result("错误: 数量必须是数字")
                    return
            
            async for result in self.list_tracks(event, count):
                yield result
                
        elif subcommand == "random":
            # 处理 random 命令
            async for result in self.random_track(event):
                yield result
                
        elif subcommand == "id":
            # 处理 id 命令
            if len(command_parts) < 3:
                yield event.plain_result("错误: 请提供歌曲ID")
                return
                
            try:
                track_id = int(command_parts[2])
            except ValueError:
                yield event.plain_result("错误: ID必须是数字")
                return
                
            async for result in self.get_track_by_id(event, track_id):
                yield result
        else:
            yield event.plain_result("未知命令。可用命令: list, random, id")

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
    
    async def fetch_playlist_data(self):
        """获取播放列表数据"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("https://music.fimall.lol/spotify_playlist_data.json")
            response.raise_for_status()
            return response.json()
    
    async def list_tracks(self, event: AstrMessageEvent, count: int):
        """列出前N首歌曲"""
        try:
            data = await self.fetch_playlist_data()
            tracks = data.get("tracks", [])
            
            if not tracks:
                yield event.plain_result("播放列表为空")
                return
            
            result_lines = []
            for i, track_item in enumerate(tracks[:count], 1):
                track = track_item.get("track", {})
                name = track.get("name", "未知曲目")
                album = track.get("album", {}).get("name", "未知专辑")
                artists = track.get("artists", [])
                artist = " & ".join([a.get("name", "未知艺术家") for a in artists])
                
                result_lines.append(f"{i} | {name} | {album} | {artist}")
            
            yield event.plain_result("\n".join(result_lines))
            
        except Exception as e:
            logger.error(f"获取歌曲列表时发生错误: {str(e)}")
            yield event.plain_result("获取歌曲列表失败")
    
    async def random_track(self, event: AstrMessageEvent):
        """获取随机歌曲"""
        try:
            data = await self.fetch_playlist_data()
            tracks = data.get("tracks", [])
            
            if not tracks:
                yield event.plain_result("播放列表为空")
                return
            
            # 随机选择一首歌
            track_item = random.choice(tracks)
            track = track_item.get("track", {})
            name = track.get("name", "未知曲目")
            album_info = track.get("album", {})
            album = album_info.get("name", "未知专辑")
            artists = track.get("artists", [])
            artist = " & ".join([a.get("name", "未知艺术家") for a in artists])
            
            # 发送文本信息
            yield event.plain_result(f"{name} | {album} | {artist}")
            
            # 发送专辑封面图片
            images = album_info.get("images", [])
            if images:
                # 选择最大尺寸的图片
                image_url = images[0].get("url")
                if image_url:
                    yield event.image_result(image_url)
            
        except Exception as e:
            logger.error(f"获取随机歌曲时发生错误: {str(e)}")
            yield event.plain_result("获取随机歌曲失败")
    
    async def get_track_by_id(self, event: AstrMessageEvent, track_id: int):
        """根据ID获取指定歌曲"""
        try:
            data = await self.fetch_playlist_data()
            tracks = data.get("tracks", [])
            total_tracks = data.get("total_tracks_retrieved", len(tracks))
            
            if not tracks:
                yield event.plain_result("播放列表为空")
                return
            
            if track_id < 1 or track_id > total_tracks:
                yield event.plain_result(f"错误: ID必须在1到{total_tracks}之间")
                return
            
            # 获取指定ID的歌曲（ID从1开始，数组从0开始）
            if track_id > len(tracks):
                yield event.plain_result(f"错误: 请求的歌曲ID({track_id})超出已加载的歌曲数量({len(tracks)})")
                return
                
            track_item = tracks[track_id - 1]
            track = track_item.get("track", {})
            name = track.get("name", "未知曲目")
            album_info = track.get("album", {})
            album = album_info.get("name", "未知专辑")
            artists = track.get("artists", [])
            artist = " & ".join([a.get("name", "未知艺术家") for a in artists])
            
            # 发送文本信息
            yield event.plain_result(f"{name} | {album} | {artist}")
            
            # 发送专辑封面图片
            images = album_info.get("images", [])
            if images:
                # 选择最大尺寸的图片
                image_url = images[0].get("url")
                if image_url:
                    yield event.image_result(image_url)
            
        except Exception as e:
            logger.error(f"获取指定歌曲时发生错误: {str(e)}")
            yield event.plain_result("获取指定歌曲失败")

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
