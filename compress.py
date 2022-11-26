#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# -----------------------------------
# @File    :  compress.py
# @Author  :  woodwhale
# @Time    :  2022/11/25 10:20:05
# -----------------------------------

import os
from rich.progress import track
from queue import PriorityQueue


class FileWriter:
    """帮助写文件的类"""

    MOD: int = 8  # 8位一模
    pos: int = 0  # 当前位置
    cur: bytes = 0  # 缓存的位数据
    total_bit: int = 0  # 压缩后写入的哈夫曼编码总位数
    total_bit_offset: int = 0  # 文件总位数存放在文件中的偏移

    def __init__(self, filename: str):
        self.filename = filename
        self.file = open(filename, "wb")

    def write_bit(self, bt: int):
        """写1位的数据, 但是每8位(1字节)才真正写一次

        :param bt: 0 or 1
        :type bt: int
        """
        assert bt in [0, 1] and self.file
        self.cur = (self.cur << 1) | bt
        self.pos += 1
        self.total_bit += 1
        if self.pos == self.MOD:  # 缓存8位写一次
            self.file.write(bytes([self.cur]))
            self.pos = self.cur = 0

    def write_int(self, val: int):
        """写4字节长度的数据, 最大为0xffffffff

        :param val: 数据
        :type val: int
        """
        assert self.file and val & 0x100000000 == 0
        self.file.write(bytes([(val & 0xFF000000) >> 24]))
        self.file.write(bytes([(val & 0x00FF0000) >> 16]))
        self.file.write(bytes([(val & 0x0000FF00) >> 8]))
        self.file.write(bytes([(val & 0x000000FF)]))

    def write_fre_head(self, fre: list):
        """写压缩后的文件头, 存储的内容是词频表, 每个词频长度为4字节

        :param fre: 词频列表
        :type fre: list
        """
        for i in fre:
            self.write_int(i)
        self.total_bit_offset = len(fre) * 4  # total_bit写的地址

    def write_total_bit(self):
        """找到存放文件总位数的地址然后写入文件总位数"""
        assert self.file
        self.file.seek(self.total_bit_offset)
        self.write_int(self.total_bit)

    def write_remind_bit(self):
        """处理还未写入的缓存数据"""
        assert self.file
        if self.pos:  # 把剩下的数据写进去
            while self.pos != self.MOD:
                self.cur = (self.cur << 1) | 0
                self.pos += 1
            self.file.write(bytes([self.cur]))

    def close(self):
        """关闭文件"""
        assert self.file
        self.file.close()  # 记得关文件


class Node:
    """哈夫曼节点"""

    def __init__(self, val: bytes, fre: int, is_leaf: bool):
        self.val = val
        self.fre = fre
        self.is_leaf = is_leaf
        self.chs = [0, 0]  # 左右孩子

    def __lt__(self, other):
        """优先队列排序方法

        :param other: 另一个哈夫曼节点
        :type other: Node
        :return: 词频小的优先级越高
        :rtype: bool
        """
        return self.fre < other.fre


class Compressor:
    """压缩器类"""

    fre: list = [0] * 0x100  # 字节频率
    total_bytes: int = 0  # 文件总大小
    encode_table: dict = dict()  # 编码hash表
    bytes_data: bytes  # 文件内容
    root: Node  # 哈夫曼树根节点

    def __init__(self, filename: str):
        assert os.path.exists(filename)
        self.filename = filename

    def gen_fre_table(self):
        """读文件, 生成词频表"""
        with open(self.filename, "rb") as f:
            self.bytes_data = f.read()
        for bt in self.bytes_data:
            self.fre[int(bt)] += 1
        self.total_bytes = len(self.bytes_data)

    def gen_tree(self):
        """生成哈夫曼树"""
        que = PriorityQueue()
        for i in range(256):
            if self.fre[i]:
                que.put(Node(bytes([i]), self.fre[i], True))
        # 优先队列获取哈夫曼树
        while len(que.queue) != 1:
            l = que.get()
            r = que.get()  # 权重最小的两个节点合并成一棵树
            tmp = Node(b"\x00", l.fre + r.fre, False)
            tmp.chs[0] = l
            tmp.chs[1] = r
            que.put(tmp)

        self.root = que.queue[0]

        # 生成哈夫曼编码
        self.dfs(self.root, b"")

    def dfs(self, node: Node, cur: bytes):
        """深度优先遍历哈夫曼树

        :param node: 哈夫曼节点
        :type node: Node
        :param cur: 当前哈夫曼编码
        :type cur: bytes
        """
        if not node:
            return
        if node.is_leaf:
            self.encode_table[node.val] = cur

        self.dfs(node.chs[0], cur + b"\x00")
        self.dfs(node.chs[1], cur + b"\x01")

    def compress(self, to_filename: str):
        """压缩文件

        :param to_filename: 压缩后文件的文件名
        :type to_filename: str
        """
        self.gen_fre_table()
        self.gen_tree()

        writer = FileWriter(to_filename)
        writer.write_fre_head(self.fre)  # 写文件结构种的频率头
        writer.write_int(0)  # 占位，用来存放文件大小的位置

        for b in track(self.bytes_data, description="Compressing..."):
            s = self.encode_table[bytes([b])]
            for i in s:  # 写每一位
                writer.write_bit(i)

        writer.write_remind_bit()  # 把剩下的东西写进去
        writer.write_total_bit()  # 把原先占位的0写上去
        writer.close()  # 关文件
        print(f"Before file bytes :  {self.total_bytes}")
        print(f"After file bytes  :  {writer.total_bit // 8}")


class Decompressor:
    fre: list = [0] * 0x100  # 字节频率
    total_bit: int = 0  # 压缩后的总位数
    encode_content: bytes  # 编码后的文件内容(除去fre头之外的文件内容)
    root: Node  # 哈夫曼树根节点

    def __init__(self, filename: str):
        assert os.path.exists(filename)
        self.filename = filename

    def read_fre_head(self):
        """读取词频头, 256*4字节"""
        with open(self.filename, "rb") as f:
            for i in range(256):  # 读fre头
                tmp = 0
                for _ in range(4):
                    tmp = (tmp << 8) | int.from_bytes(f.read(1), "little")
                self.fre[i] = tmp
            tmp = 0
            for _ in range(4):  # 读total bytes
                tmp = (tmp << 8) | int.from_bytes(f.read(1), "little")
            self.total_bit = tmp
            self.encode_content = f.read()  # 剩下的文件大小都是编码后内容

    def gen_tree(self):
        """根据词频生成哈夫曼树"""
        que = PriorityQueue()
        for i in range(256):
            if self.fre[i]:
                que.put(Node(bytes([i]), self.fre[i], True))

        while len(que.queue) != 1:
            l = que.get()
            r = que.get()  # 权重最小的两个节点合并成一棵树
            tmp = Node(b"\x00", l.fre + r.fre, False)
            tmp.chs[0] = l
            tmp.chs[1] = r
            que.put(tmp)

        # 解码无需解码表, 之后遍历哈夫曼树就可以获取值
        self.root = que.queue[0]

    def decompress(self, to_filename: str):
        """解压文件

        :param to_filename: 解压后的文件名
        :type to_filename: str
        """
        self.read_fre_head()
        self.gen_tree()

        file = open(to_filename, "wb")
        tmp_node = self.root
        processed = 0
        # 读取哈夫曼编码部分, 进行解码的同时写入文件
        for b in track(self.encode_content, description="decompressing..."):
            # 每次读8位, 如果剩下的小于8位就写剩下的位
            for i in range(min(self.total_bit - processed, 8)):
                tmp_node = tmp_node.chs[1 if (b & (1 << (8 - i - 1))) else 0]
                if tmp_node.is_leaf:  # 叶子节点的时候才有val
                    file.write(tmp_node.val)
                    tmp_node = self.root
            processed += 8
        file.close()  # 关文件
        print("decompress successfully!")


if __name__ == "__main__":
    c = Compressor("flag")
    c.compress("encode_flag")
    d = Decompressor("encode_flag")
    d.decompress("decode_flag")
