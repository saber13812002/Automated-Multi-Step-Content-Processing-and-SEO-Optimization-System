from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class AudioMaster(Base):
    __tablename__ = "audio_master"

    audio_guid: Mapped[str] = mapped_column(String(64), primary_key=True)
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    approved_text: Mapped[str] = mapped_column(Text, nullable=False)

    transcriptions: Mapped[list["Transcription"]] = relationship(
        back_populates="audio",
        cascade="all, delete-orphan",
    )
    benchmark_results: Mapped[list["BenchmarkResult"]] = relationship(
        back_populates="audio",
        cascade="all, delete-orphan",
    )


class Transcription(Base):
    __tablename__ = "transcription"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    audio_guid: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("audio_master.audio_guid"),
        nullable=False,
    )
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[str] = mapped_column(Text, nullable=False)

    audio: Mapped["AudioMaster"] = relationship(back_populates="transcriptions")
    benchmarks_as_ref: Mapped[list["BenchmarkResult"]] = relationship(
        back_populates="reference",
        foreign_keys="BenchmarkResult.ref_id",
    )
    benchmarks_as_hyp: Mapped[list["BenchmarkResult"]] = relationship(
        back_populates="hypothesis",
        foreign_keys="BenchmarkResult.hyp_id",
    )


class BenchmarkResult(Base):
    __tablename__ = "benchmark_result"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    audio_guid: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("audio_master.audio_guid"),
        nullable=False,
    )
    ref_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("transcription.id"),
        nullable=False,
    )
    hyp_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("transcription.id"),
        nullable=False,
    )
    wer: Mapped[float] = mapped_column(Float, nullable=False)
    ngram_bigram: Mapped[float] = mapped_column(Float, nullable=False)
    ngram_trigram: Mapped[float] = mapped_column(Float, nullable=False)
    lcs_score: Mapped[float] = mapped_column(Float, nullable=False)

    audio: Mapped["AudioMaster"] = relationship(back_populates="benchmark_results")
    reference: Mapped["Transcription"] = relationship(
        back_populates="benchmarks_as_ref",
        foreign_keys=[ref_id],
    )
    hypothesis: Mapped["Transcription"] = relationship(
        back_populates="benchmarks_as_hyp",
        foreign_keys=[hyp_id],
    )
