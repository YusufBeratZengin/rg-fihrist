"""Regression tests for the publication contract and test infrastructure.

Windows gecici test ciktilarinin varligi urun davranisi degildir.
"""

from pathlib import Path

from rg_fihrist import cli, indir

KOK = Path(__file__).parents[1]


def test_yayin_ag_kodu_ve_indirici_protokolu_korunur() -> None:
    assert getattr(cli, "CIKIS_AG", None) == 2
    assert hasattr(indir, "IndiriciProtokolu")


def test_yayin_ci_kapilari_korunur() -> None:
    ci = (KOK / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    for parca in (
        "windows-latest",
        "permissions:",
        "contents: read",
        "concurrency:",
        "cancel-in-progress: true",
        "python -m ruff check .",
        "python -m ruff format --check .",
        "python -m mypy",
        "bash scripts/check.sh",
    ):
        assert parca in ci


def test_yayin_gitignore_ve_kullanim_belgesi_korunur() -> None:
    kurallar = (KOK / ".gitignore").read_text(encoding="utf-8").splitlines()
    for kural in (".tmp/", "*.log", "HAT-*.md"):
        assert kural in kurallar
    readme = (KOK / "README.md").read_text(encoding="utf-8")
    for baslik in ("## Exit codes", "## Known limits", "### Turkish search semantics"):
        assert baslik in readme


def test_test_paketi_modul_eslemesi_tek_anlamli() -> None:
    # tests.conftest importlari ile mypy'nin conftest eslemesi ayni paket olmali.
    assert (KOK / "tests" / "__init__.py").is_file()


def test_modern_ilan_girdileri_gezinmeden_ayrilir() -> None:
    from rg_fihrist.ayristir import ayristir

    html = (
        "<div class='html-title'>İLÂN BÖLÜMÜ</div>"
        "<div class='fihrist-item'><a href='/ilanlar/eskiilanlar/2026/11/20261102-2.htm'>"
        "a - Yargı İlânları</a></div>"
        "<a href='/fihrist?tarih=2026-11-01'>Önceki Sayı</a>"
        "<a href='/eskiler/2026/11/20261102.pdf'>PDF Görüntüle</a>"
    )
    fihrist = ayristir(html, "https://ornek.test/fihrist?tarih=2026-11-02")
    assert [g.baslik for g in fihrist.girdiler] == ["a - Yargı İlânları"]
    assert fihrist.girdiler[0].alt_baslik is None


def test_eski_ilan_girdisinden_sonra_gezinme_eklenmez() -> None:
    from rg_fihrist.ayristir import ayristir

    html = (
        "<b><u>İLÂN BÖLÜMÜ</u></b>"
        "<a href='/ilanlar/eskiilanlar/2026/11/20261102-2.htm'>a - Yargı İlânları</a>"
        "<a href='/eskiler/2026/11/20261101.htm'>Önceki Sayı</a>"
        "<a href='/eskiler/2026/11/20261102.pdf'>PDF Görüntüle</a>"
    )
    fihrist = ayristir(html, "https://ornek.test/eskiler/2026/11/20261102.htm")
    assert [g.baslik for g in fihrist.girdiler] == ["a - Yargı İlânları"]
