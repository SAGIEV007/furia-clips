from modules.headline_quote import _disqualify, headline_fragment_reason
from modules.headline_studio import FORMAT_VERTICAL, generate_artwork_copy


SRT_0827 = """1
00:00:16,066 --> 00:00:17,466
então eu pergunto ao senhor

2
00:00:17,566 --> 00:00:19,300
o que permite ao senhor

3
00:00:19,600 --> 00:00:22,600
dizer que é possível implantar esse seu plano

4
00:00:22,933 --> 00:00:23,733
ao mesmo tempo

5
00:00:24,200 --> 00:00:26,933
em todo país e nesse prazo de um ano?

6
00:00:27,533 --> 00:00:28,300
grande pergunta

7
00:00:28,300 --> 00:00:29,266
César vamo lá

8
00:00:29,300 --> 00:00:30,466
o Brasil vive uma guerra

9
00:00:30,566 --> 00:00:32,566
é uma guerra que foi declarado unilateralmente

10
00:00:32,733 --> 00:00:34,333
o crime organizado tá em guerra com você

11
00:00:34,333 --> 00:00:35,200
que tá nos assistindo

12
00:00:35,800 --> 00:00:37,000
e você fica considerando

13
00:00:37,100 --> 00:00:39,800
vamos dizer que tua vida é ser refém

14
00:00:39,933 --> 00:00:41,066
se você mora numa favela

15
00:00:41,133 --> 00:00:42,366
o crime organizado manda em você

16
00:00:42,500 --> 00:00:44,066
pode te desalojar da tua casa

17
00:00:44,600 --> 00:00:45,700
pode eventualmente

18
00:00:45,733 --> 00:00:48,266
se interessar de maneira sexual pela tua filha

19
00:00:48,333 --> 00:00:49,533
e você não tem como se defender

20
00:00:49,900 --> 00:00:52,666
a vida no país que tá em guerra é uma vida triste

21
00:00:53,300 --> 00:00:55,133
hoje quase quarenta milhões de brasileiros vivem

22
00:00:55,266 --> 00:00:56,400
direta ou indiretamente

23
00:00:56,466 --> 00:00:57,966
sobre a influência do crime organizado

24
00:00:58,333 --> 00:00:58,666
portanto

25
00:00:58,666 --> 00:01:00,100
o que eu defendo é a criação

26
00:01:00,466 --> 00:01:02,166
e a declaração de uma guerra

27
00:01:02,766 --> 00:01:03,733
contra o crime organizado

28
00:01:03,766 --> 00:01:05,700
é aceitação de uma realidade que já é verdadeira

29
00:01:05,766 --> 00:01:06,566
pros brasileiros

30
00:01:06,766 --> 00:01:08,033
precisamos de uma guerra contra eles

31
00:01:08,033 --> 00:01:08,666
antes da da

32
00:01:08,666 --> 00:01:09,566
gLO do temer

33
00:01:09,766 --> 00:01:11,633
nós tivemos as upps aqui no Rio de Janeiro

34
00:01:11,666 --> 00:01:13,100
que foram uma outra tentativa de

35
00:01:13,500 --> 00:01:15,666
entrar em áreas é tomadas pelo crime organizado

36
00:01:15,866 --> 00:01:16,466
que no início

37
00:01:16,466 --> 00:01:18,433
obtiveram sucesso com as operações do BOPE

38
00:01:18,666 --> 00:01:19,933
e depois não deram certo porque

39
00:01:20,266 --> 00:01:22,433
porque o Brasil não fez um arcabouço legal

40
00:01:22,833 --> 00:01:24,633
pra permitir a continuidade desse processo
"""


def _suggestions():
    result = generate_artwork_copy(
        SRT_0827,
        mini_context="Fala de Renan Santos sobre segurança pública, crime organizado e guerra contra o crime.",
        preferred_format=FORMAT_VERTICAL,
        ai_backend=None,
    )
    return result, result["formats"][FORMAT_VERTICAL]["suggestions"]


def test_fragment_and_possible_asr_reasons_are_stable():
    assert headline_fragment_reason("Portanto o que eu defendo é a criação") == (
        "começa como continuação da frase anterior"
    )
    assert "concordância" in headline_fragment_reason(
        "Entrar em áreas é tomadas pelo crime organizado"
    )
    assert _disqualify("Para permitir a continuidade desse processo", False, False)


def test_0827_headlines_do_not_promote_the_known_fragments():
    result, suggestions = _suggestions()
    headlines = [item["headline"].lower() for item in suggestions]
    assert not any("portanto o que eu defendo é a criação" in item for item in headlines)
    assert not any("para permitir a continuidade" in item for item in headlines)
    assert not any("é tomadas" in item for item in headlines)
    assert any("guerra" in item for item in headlines)
    assert result["review_flags"]["source_not_punctuated"] is True


def test_0827_suggestions_expose_fidelity_and_audio_review_metadata():
    result, suggestions = _suggestions()
    assert suggestions
    assert all("headline_review" in item for item in suggestions)
    assert all("source_interval" in item for item in suggestions)
    assert result["fidelity"]["audio_review_count"] >= 1
    assert result["fidelity"]["fragment_review_count"] == 0


def test_srt_timestamp_reset_is_reported_to_the_editor():
    discontinuous = SRT_0827 + """

41
00:00:00,333 --> 00:00:01,366
na segurança pública
"""
    result = generate_artwork_copy(
        discontinuous,
        mini_context="Fala de Renan Santos sobre segurança pública.",
        preferred_format=FORMAT_VERTICAL,
        ai_backend=None,
    )
    review = result["transcript"]["timeline_review"]
    assert review["timeline_status"] == "discontinuous"
    assert review["timestamp_reset_count"] == 1
    assert result["review_flags"]["timestamp_discontinuity"] is True
    assert result["review_flags"]["timestamp_discontinuity_count"] == 1
