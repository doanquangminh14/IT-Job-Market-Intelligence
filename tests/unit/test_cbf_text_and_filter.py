from sklearn.feature_extraction.text import TfidfVectorizer

from src.data_cleaning.it_filter import is_it_job
from src.data_cleaning.skill_canonical import extract_skills_from_text
from src.recommender.text_utils import normalize_tech_text, TOKEN_PATTERN


def _tokens(text):
    return TfidfVectorizer(preprocessor=normalize_tech_text, token_pattern=TOKEN_PATTERN).build_analyzer()(text)


def test_tokenizer_keeps_cpp_csharp_dotnet_distinct():
    toks = _tokens("C++ C# .NET CI/CD Node.js")
    assert {"cpp", "csharp", "dotnet", "cicd", "nodejs"} <= set(toks)


def test_tokenizer_keeps_vietnamese_words():
    assert "nghiệm" in _tokens("kinh nghiệm lập trình")


def test_extract_skills_special_chars_and_ambiguity():
    skills = extract_skills_from_text("C++, C#, .NET Core, CI/CD. Gửi CV. Go to market")
    assert {"C++", "C#", ".NET", "CI/CD"} <= set(skills)
    assert "Computer Vision" not in skills and "Golang" not in skills


def test_it_filter():
    assert is_it_job("Senior Backend Developer", "")
    assert is_it_job("Chuyên viên", "Python, SQL")
    assert not is_it_job("Nhân viên thiết kế đồ họa", "Photoshop, Illustrator")
    assert not is_it_job("Nhân viên kinh doanh", float("nan"))


def test_it_filter_game_and_digital_art():
    # Phạm vi mở rộng: game & đồ họa kỹ thuật số
    for title in ["Game Designer Intern", "2D Animator", "3D Rigger", "Unreal Engine Artist",
                  "2D Game Artist - Junior", "3D Character Modeler", "Nhân Viên Thiết Kế Game ( Fresher)"]:
        assert is_it_job(title, ""), title
    # Vẫn không phải IT: đồ họa in ấn, thiết kế sự kiện/nội thất 3D, vận hành/kinh doanh game
    for title in ["Graphic Designer", "Nhân Viên Thiết Kế 3D (Event & Activation)",
                  "Chuyên Viên Thiết Kế Nội Thất 3D", "Nhân Viên Vận Hành Game"]:
        assert not is_it_job(title, ""), title
