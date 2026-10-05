// =============================================================================
//  Cobras e Escadas (tabuleiro 6x6, casas 1..36) — solução computacional em C++
// =============================================================================
//  1. Monte Carlo: 10.000 partidas por cenário (como pede o enunciado),
//     com IC 95% (Wilson p/ proporções, normal p/ médias).
//  2. Validação: solução EXATA por cadeia de Markov absorvente; o programa
//     confere que o valor exato cai no IC da simulação em todas as perguntas.
//  3. Testes unitários do motor com dados roteirizados.
//
//  Compilar:  g++ -std=c++17 -O2 -Wall -Wextra -o cobras cobras_escadas.cpp
//  Rodar:     ./cobras [n_jogos] [semente]        (padrão: 10000 2026)
// =============================================================================
#include <algorithm>
#include <array>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <random>
#include <string>
#include <vector>

// ------------------------------------------------------------------ tabuleiro
constexpr int ULTIMA = 36;
struct Atalho { int de, para; };
constexpr std::array<Atalho, 5> ESCADAS{{{3, 16}, {5, 7}, {15, 25}, {18, 20}, {21, 32}}};
constexpr std::array<Atalho, 5> COBRAS {{{12, 2}, {14, 11}, {17, 4}, {31, 19}, {35, 22}}};

enum class Tipo { Normal, Escada, Cobra };

struct Tabuleiro {
    std::array<int, ULTIMA + 1> destino{};
    std::array<Tipo, ULTIMA + 1> tipo{};
    Tabuleiro() {
        for (int c = 0; c <= ULTIMA; ++c) { destino[c] = c; tipo[c] = Tipo::Normal; }
        for (auto [a, b] : ESCADAS) { destino[a] = b; tipo[a] = Tipo::Escada; }
        for (auto [a, b] : COBRAS)  { destino[a] = b; tipo[a] = Tipo::Cobra; }
        // validação estrutural da leitura
        for (auto [a, b] : ESCADAS) assert(a < b && "escada tem que subir");
        for (auto [a, b] : COBRAS)  assert(a > b && "cobra tem que descer");
        for (int c = 1; c <= ULTIMA; ++c)   // sem encadeamento de atalhos
            if (tipo[c] != Tipo::Normal) assert(tipo[destino[c]] == Tipo::Normal);
    }
    bool gatilho(int c) const { return tipo[c] != Tipo::Normal; }
};
static const Tabuleiro TAB;

// --------------------------------------------------------------------- regras
struct Regras {
    int    inicio_j2   = 1;
    double p_escada    = 1.0;    // Q3: 0.5
    bool   imunidade_j2 = false; // Q5
};

// ---------------------------------------------------------------- aleatório
// Interface mínima: dado() em 1..6 e uniforme() em [0,1).
class Rng {
    std::mt19937_64 g_;
    std::uniform_int_distribution<int> d6_{1, 6};
    std::uniform_real_distribution<double> u_{0.0, 1.0};
public:
    explicit Rng(std::uint64_t semente) : g_(semente) {}
    int dado() { return d6_(g_); }
    double uniforme() { return u_(g_); }
};

// --------------------------------------------------------------------- motor
struct Jogador {
    int casa;
    bool imune = false;
    int lances = 0, cobras = 0, escadas = 0;

    // Executa um lance; devolve true se venceu (chegou ou passou de 36).
    template <class R>
    bool jogar(R& rng, double p_escada) {
        ++lances;
        int d = std::min(casa + rng.dado(), ULTIMA);
        switch (TAB.tipo[d]) {
            case Tipo::Escada:
                // p == 1 não consome sorteio (mantém fluxos comparáveis)
                if (p_escada >= 1.0 || rng.uniforme() < p_escada) { d = TAB.destino[d]; ++escadas; }
                break;
            case Tipo::Cobra:
                if (imune) imune = false;               // fica na cabeça
                else { d = TAB.destino[d]; ++cobras; }
                break;
            case Tipo::Normal: break;
        }
        casa = d;
        return casa == ULTIMA;
    }
};

struct Partida { int vencedor, lances, cobras_j1, cobras_j2; };

template <class R>
Partida jogar_partida(const Regras& r, R& rng) {
    std::array<Jogador, 2> j{Jogador{1}, Jogador{r.inicio_j2, r.imunidade_j2}};
    int vez = 0;
    while (!j[vez].jogar(rng, r.p_escada)) vez ^= 1;
    return {vez + 1, j[0].lances + j[1].lances, j[0].cobras, j[1].cobras};
}

// ------------------------------------------------------------ estatística
constexpr double Z95 = 1.959963984540054;

struct IC { double est, inf, sup; bool contem(double x) const { return inf <= x && x <= sup; } };

IC wilson(long k, long n) {
    double p = double(k) / n, z2 = Z95 * Z95, den = 1 + z2 / n;
    double c = (p + z2 / (2.0 * n)) / den;
    double m = Z95 * std::sqrt(p * (1 - p) / n + z2 / (4.0 * n * n)) / den;
    return {p, c - m, c + m};
}

struct Media {                      // Welford: média e variância estáveis
    long n = 0; double m = 0, s2 = 0;
    void add(double x) { ++n; double d = x - m; m += d / n; s2 += d * (x - m); }
    IC ic() const { double e = Z95 * std::sqrt(s2 / (n - 1) / n); return {m, m - e, m + e}; }
};

struct Resumo { long n = 0, vitorias_j1 = 0; Media lances, cobras, cobras_j1, cobras_j2; };

Resumo simular(const Regras& r, long n, std::uint64_t semente) {
    Rng rng(semente);
    Resumo s; s.n = n;
    for (long i = 0; i < n; ++i) {
        Partida p = jogar_partida(r, rng);
        s.vitorias_j1 += (p.vencedor == 1);
        s.lances.add(p.lances);
        s.cobras.add(p.cobras_j1 + p.cobras_j2);
        s.cobras_j1.add(p.cobras_j1);
        s.cobras_j2.add(p.cobras_j2);
    }
    return s;
}

// ======================================================= solução exata (Markov)
// Estado = casa + 37*gasta (gasta=1: sem imunidade). Propaga a distribuição
// lance a lance e guarda, p/ um jogador isolado:
//   f[n] = P(T = n+1),  S[n] = P(T > n),  s[n] = P(cobra no lance n+1).
constexpr int NMAX = 4000;          // cauda ~ 0.81^n -> truncamento desprezível
constexpr int K = 2 * (ULTIMA + 1);

struct Dist { std::vector<double> f, S, s; };

Dist jogador_exato(int inicio, double p_escada, bool imune) {
    auto idx = [](int c, int gasta) { return c + (ULTIMA + 1) * gasta; };
    std::vector<double> v(K, 0.0), w(K);
    v[idx(inicio, imune ? 0 : 1)] = 1.0;
    auto fim = [&](const std::vector<double>& x) { return x[idx(ULTIMA, 0)] + x[idx(ULTIMA, 1)]; };

    Dist D{std::vector<double>(NMAX), std::vector<double>(NMAX + 1), std::vector<double>(NMAX)};
    D.S[0] = 1.0 - fim(v);
    for (int n = 0; n < NMAX; ++n) {
        std::fill(w.begin(), w.end(), 0.0);
        double cobra = 0.0;
        for (int g = 0; g < 2; ++g) {
            w[idx(ULTIMA, g)] += v[idx(ULTIMA, g)];            // absorvente
            for (int i = 1; i < ULTIMA; ++i) {
                double pi = v[idx(i, g)];
                if (pi == 0.0) continue;
                for (int d = 1; d <= 6; ++d) {
                    int j = std::min(i + d, ULTIMA);
                    double q = pi / 6.0;
                    switch (TAB.tipo[j]) {
                        case Tipo::Cobra:
                            if (g == 0) w[idx(j, 1)] += q;              // usa imunidade
                            else { w[idx(TAB.destino[j], 1)] += q; cobra += q; }
                            break;
                        case Tipo::Escada:
                            w[idx(TAB.destino[j], g)] += q * p_escada;
                            w[idx(j, g)]              += q * (1.0 - p_escada);
                            break;
                        case Tipo::Normal:
                            w[idx(j, g)] += q;
                    }
                }
            }
        }
        D.s[n] = cobra;
        v.swap(w);
        D.S[n + 1] = 1.0 - fim(v);
        D.f[n] = D.S[n] - D.S[n + 1];
    }
    return D;
}

// J1 joga primeiro.  J1 vence no seu lance n  <=> T1 = n e T2 >= n.
double exato_p_j1(const Dist& a, const Dist& b) {
    double p = 0; for (int n = 0; n < NMAX; ++n) p += a.f[n] * b.S[n]; return p;
}
// J1 joga o lance n se T2 >= n; J2 joga o lance n se T1 > n.
double exato_cobras(const Dist& a, const Dist& b) {
    double e = 0; for (int n = 0; n < NMAX; ++n) e += a.s[n] * b.S[n] + b.s[n] * a.S[n + 1]; return e;
}
// J1 vence no lance n -> 2n-1 lances; J2 vence no lance n -> 2n lances.
double exato_lances(const Dist& a, const Dist& b) {
    double e = 0;
    for (int n = 0; n < NMAX; ++n) {
        int k = n + 1;
        e += a.f[n] * b.S[n] * (2 * k - 1) + b.f[n] * a.S[n + 1] * (2 * k);
    }
    return e;
}

// ======================================================= testes do motor
struct DadoRoteirizado {
    std::vector<int> dados; std::vector<double> sorteios; size_t i = 0, j = 0;
    int dado() { return dados.at(i++); }
    double uniforme() { return sorteios.at(j++); }
};

void testes() {
    auto lance = [](int casa, int d, double p = 1.0, bool imune = false,
                    std::vector<double> sort = {}) {
        Jogador jg{casa, imune};
        DadoRoteirizado r{{d}, sort};
        bool v = jg.jogar(r, p);
        return std::array<int, 4>{jg.casa, v, jg.cobras, jg.imune};
    };
    auto ok = [](bool c, const char* m) { if (!c) { std::fprintf(stderr, "FALHOU: %s\n", m); std::exit(1); } };
    ok(lance(1, 2)[0] == 16,                         "escada 3->16");
    ok(lance(1, 4)[0] == 7,                          "escada 5->7");
    ok(lance(10, 4)[0] == 11,                        "cobra 14->11");
    ok(lance(30, 5)[0] == 22 && lance(30, 5)[2] == 1, "cobra 35->22 conta 1");
    ok(lance(33, 6)[0] == 36 && lance(33, 6)[1],      "passar de 36 vence");
    ok(lance(30, 6)[1],                              "cair exato em 36 vence");
    ok(lance(1, 2, .5, false, {.7})[0] == 3,          "escada falha: fica na base");
    ok(lance(1, 2, .5, false, {.2})[0] == 16,         "escada funciona");
    ok((lance(10, 2, 1, true) == std::array<int, 4>{12, 0, 0, 0}), "imunidade usada");
    ok(lance(10, 2)[0] == 2,                         "cobra 12->2");
    // J1 1->3->16 | J2 1->2 | J1 16->21->32 | J2 2->3->16 | J1 32->36
    DadoRoteirizado r{{2, 1, 5, 1, 4}, {}};
    Partida p = jogar_partida(Regras{}, r);
    ok(p.vencedor == 1 && p.lances == 5, "partida roteirizada");
    std::puts("Testes do motor: OK");
}

// ===================================================================== main
int main(int argc, char** argv) {
    const long N = argc > 1 ? std::atol(argv[1]) : 10000;
    const std::uint64_t SEED = argc > 2 ? std::strtoull(argv[2], nullptr, 10) : 2026;

    testes();
    std::printf("Monte Carlo: %ld partidas/cenario, semente %llu\n\n", N, (unsigned long long)SEED);

    const Dist J = jogador_exato(1, 1.0, false);
    bool tudo_ok = true;
    // Critério de aprovação: |z| < 3.5 (o IC 95% sozinho falharia ~5% das
    // vezes por puro acaso; com 5 checagens isso viraria alarme falso comum).
    auto linha = [&](const char* nome, IC ic, double ex, int dec) {
        double se = (ic.sup - ic.inf) / (2 * Z95), z = (ic.est - ex) / se;
        bool c = std::fabs(z) < 3.5; tudo_ok &= c;
        std::printf("%-34s %8.*f  [%.*f, %.*f]   exato %8.*f  z=%+5.2f %s\n",
                    nome, dec, ic.est, dec, ic.inf, dec, ic.sup, dec, ex, z, c ? "ok" : "DIVERGE");
    };

    // Q1
    Resumo base = simular(Regras{}, N, SEED + 1);
    linha("Q1 P(J1 vence)", wilson(base.vitorias_j1, N), exato_p_j1(J, J), 4);

    // Q2
    linha("Q2 cobras/partida (J1+J2)", base.cobras.ic(), exato_cobras(J, J), 3);
    std::printf("     J1 %.3f | J2 %.3f\n", base.cobras_j1.ic().est, base.cobras_j2.ic().est);

    // Q3
    Regras r3; r3.p_escada = 0.5;
    const Dist J3 = jogador_exato(1, 0.5, false);
    Resumo q3 = simular(r3, N, SEED + 3);
    linha("Q3 lances/partida (escada 50%)", q3.lances.ic(), exato_lances(J3, J3), 2);
    std::printf("     ref. escada 100%%: %.2f (exato %.2f)\n", base.lances.ic().est, exato_lances(J, J));

    // Q4 — duas etapas.
    //  (1) Triagem: 10^4 jogos em cada casa candidata (mesma semente).
    //  (2) Refinamento: as casas compatíveis com 0.5 (|z| < 3) são re-simuladas
    //      com N2 jogos. Motivo: P(J1) nas casas 7 e 8 difere só ~0.009, menor
    //      que a resolução de 10^4 jogos (IC ~ ±0.01) — só a triagem escolhe a
    //      casa errada em ~40% das sementes.
    std::puts("\nQ4 P(J1 vence) x casa inicial do J2  (etapa 1: triagem)");
    const long N2 = std::max(500000L, N);
    struct Cand { int casa; double ex; };
    std::vector<Cand> finalistas;
    double ex_melhor = 9; int melhor_ex = -1;
    for (int c = 1; c < ULTIMA; ++c) {
        if (TAB.gatilho(c)) continue;          // peça nunca repousa em gatilho
        Regras r; r.inicio_j2 = c;
        IC ic = wilson(simular(r, N, SEED + 4).vitorias_j1, N);
        double ex = exato_p_j1(J, jogador_exato(c, 1.0, false));
        double se = (ic.sup - ic.inf) / (2 * Z95);
        bool fin = std::fabs(ic.est - .5) < 3 * se;
        if (fin) finalistas.push_back({c, ex});
        if (std::fabs(ex - .5) < ex_melhor) { ex_melhor = std::fabs(ex - .5); melhor_ex = c; }
        if (c <= 13)
            std::printf("   casa %2d: %.4f [%.4f, %.4f]  exato %.4f %s\n",
                        c, ic.est, ic.inf, ic.sup, ex, fin ? "<- finalista" : "");
    }
    std::printf("   etapa 2: %zu finalistas x %ld jogos\n", finalistas.size(), N2);
    int melhor_mc = -1; double dmc = 9;
    for (auto& f : finalistas) {
        Regras r; r.inicio_j2 = f.casa;
        IC ic = wilson(simular(r, N2, SEED + 40).vitorias_j1, N2);
        std::printf("   casa %2d: %.4f [%.4f, %.4f]  exato %.4f\n", f.casa, ic.est, ic.inf, ic.sup, f.ex);
        if (std::fabs(ic.est - .5) < dmc) { dmc = std::fabs(ic.est - .5); melhor_mc = f.casa; }
    }
    bool q4ok = (melhor_mc == melhor_ex); tudo_ok &= q4ok;
    std::printf("   melhor casa: MC = %d | exato = %d  %s\n\n", melhor_mc, melhor_ex, q4ok ? "ok" : "DIVERGE");

    // Q5
    Regras r5; r5.imunidade_j2 = true;
    Resumo q5 = simular(r5, N, SEED + 5);
    linha("Q5 P(J1 vence), J2 imune", wilson(q5.vitorias_j1, N),
          exato_p_j1(J, jogador_exato(1, 1.0, true)), 4);

    std::printf("\nValidacao MC x exato: %s\n", tudo_ok ? "TODAS OK" : "HA DIVERGENCIAS");
    return tudo_ok ? 0 : 2;
}
