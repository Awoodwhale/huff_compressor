# Huffman Compressor


## Before All

This is a compressor implemented by Huffman coding algorithm using Python3.

The reason for writing this Python file is that I watched a video of some big guy who talked about a compressor implemented Java.

And I want write a Python3 version to improve my coding level.

## File Format

The first 256 * 4 bytes of the compressed file format is a word frequency table, which is used to mark the frequency of each character. The 247 * 4 bytes are used to store the length of all bits after Huffman coding, and all the remaining bytes are the 01 strings after Huffman coding and compression.

## How to use?

The `compress.py` has a class named `Compressor` and a class named `Decompressor`.

You can use these two object to compress or decompress, like below.

```python
c = Compressor("flag")
c.compress("encode_flag")
d = Decompressor("encode_flag")
d.decompress("decode_flag")
```

## More info

This Python file only realizes the compression of word frequency not exceeding 4 bytes, because word frequency exceeding this size will overflow, leading to the failure of word frequency analysis. In the future, the improved version may choose the dynamic byte length according to the files to be compressed.

## Links

[手把手带你实现一个文件压缩器，并公开处刑自己10年前的代码](https://www.bilibili.com/video/BV1ZG4y1Z7b2)
