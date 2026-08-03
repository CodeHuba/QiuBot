"""
知识库管理器

管理向量数据库和文档检索
"""
import os
from pathlib import Path
from typing import List, Optional

from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain.schema import Document


class KnowledgeBaseManager:
    """知识库管理器"""

    def __init__(self):
        self.vectorstore: Optional[FAISS] = None
        self.embeddings: Optional[HuggingFaceEmbeddings] = None
        self.kb_path = Path(__file__).parent.parent.parent / "data" / "knowledge_base"
        self.index_path = Path(__file__).parent.parent.parent / "data" / "faiss_index"

    async def initialize(self):
        """初始化知识库"""
        print("[KB] 正在初始化知识库...")

        # 1. 初始化 Embedding 模型
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        print("[KB] ✓ Embedding 模型加载完成")

        # 2. 尝试加载已有索引
        if self.index_path.exists():
            try:
                self.vectorstore = FAISS.load_local(
                    str(self.index_path),
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                print(f"[KB] ✓ 从缓存加载向量索引: {self.index_path}")
                return
            except Exception as e:
                print(f"[KB] ⚠️ 加载缓存失败: {e}，将重新构建")

        # 3. 如果没有索引，构建新的
        await self.build_index()

    async def build_index(self):
        """构建向量索引"""
        print("[KB] 正在构建向量索引...")

        # 1. 检查知识库目录
        if not self.kb_path.exists():
            print(f"[KB] ⚠️ 知识库目录不存在: {self.kb_path}")
            print("[KB] 创建空向量库...")
            # 创建一个空的向量库（带示例文档）
            sample_docs = [
                Document(
                    page_content="这是一个示例文档。请在 data/knowledge_base/ 目录下添加你的知识库文件。",
                    metadata={"source": "sample"}
                )
            ]
            self.vectorstore = FAISS.from_documents(sample_docs, self.embeddings)
            self._save_index()
            return

        # 2. 加载文档
        try:
            documents = self._load_documents()
            if not documents:
                print("[KB] ⚠️ 未找到任何文档")
                # 创建空向量库
                sample_docs = [Document(page_content="空知识库", metadata={})]
                self.vectorstore = FAISS.from_documents(sample_docs, self.embeddings)
                self._save_index()
                return

            print(f"[KB] 加载了 {len(documents)} 个文档")

            # 3. 分块
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=50,
                separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
            )
            splits = text_splitter.split_documents(documents)
            print(f"[KB] 分块后得到 {len(splits)} 个文本块")

            # 4. 向量化
            print("[KB] 正在向量化...")
            self.vectorstore = FAISS.from_documents(splits, self.embeddings)

            # 5. 保存索引
            self._save_index()

            print("[KB] ✓ 向量索引构建完成")

        except Exception as e:
            print(f"[KB] ❌ 构建索引失败: {e}")
            import traceback
            traceback.print_exc()

    def _load_documents(self) -> List[Document]:
        """加载文档"""
        documents = []

        # 支持的文件类型
        glob_patterns = ["**/*.txt", "**/*.md"]

        for pattern in glob_patterns:
            try:
                loader = DirectoryLoader(
                    str(self.kb_path),
                    glob=pattern,
                    loader_cls=TextLoader,
                    loader_kwargs={"encoding": "utf-8"}
                )
                docs = loader.load()
                documents.extend(docs)
                print(f"[KB] 从 {pattern} 加载了 {len(docs)} 个文档")
            except Exception as e:
                print(f"[KB] ⚠️ 加载 {pattern} 失败: {e}")

        return documents

    def _save_index(self):
        """保存向量索引"""
        try:
            self.index_path.parent.mkdir(parents=True, exist_ok=True)
            self.vectorstore.save_local(str(self.index_path))
            print(f"[KB] ✓ 向量索引已保存到: {self.index_path}")
        except Exception as e:
            print(f"[KB] ⚠️ 保存索引失败: {e}")

    def search(self, query: str, k: int = 3) -> List[Document]:
        """
        搜索知识库

        Args:
            query: 查询文本
            k: 返回结果数量

        Returns:
            相关文档列表
        """
        if self.vectorstore is None:
            return []

        try:
            docs = self.vectorstore.similarity_search(query, k=k)
            return docs
        except Exception as e:
            print(f"[KB] 搜索失败: {e}")
            return []

    async def add_document(self, content: str, metadata: dict = None):
        """
        添加单个文档到知识库

        Args:
            content: 文档内容
            metadata: 元数据
        """
        if self.vectorstore is None:
            print("[KB] 向量库未初始化")
            return

        doc = Document(page_content=content, metadata=metadata or {})

        try:
            self.vectorstore.add_documents([doc])
            self._save_index()
            print("[KB] ✓ 文档已添加到知识库")
        except Exception as e:
            print(f"[KB] 添加文档失败: {e}")

    async def rebuild(self):
        """重建索引"""
        print("[KB] 正在重建索引...")
        await self.build_index()


# 测试
if __name__ == "__main__":
    import asyncio

    async def test():
        manager = KnowledgeBaseManager()
        await manager.initialize()

        # 测试搜索
        results = manager.search("The Bazaar 最强英雄", k=2)
        print(f"\n搜索结果 ({len(results)} 个):")
        for i, doc in enumerate(results):
            print(f"\n[{i+1}] {doc.page_content[:100]}...")
            print(f"    元数据: {doc.metadata}")

    asyncio.run(test())
