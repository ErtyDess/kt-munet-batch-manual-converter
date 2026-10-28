const DIFFICULTY_STD = {
  0: "Basic",
  1: "Advanced",
  2: "Expert",
  3: "Master",
  4: "Re:Master",
};
const DIFFICULTY_DX = {
  0: "DX Basic",
  1: "DX Advanced",
  2: "DX Expert",
  3: "DX Master",
  4: "DX Re:Master",
};

const DX_THRESHOLD = 10000;
const UTAGE_LEVEL = 10;
const NOTE_TYPES = ["tap", "hold", "slide", "touch", "break"];

function getDifficulty(musicId, level) {
  const table = musicId >= DX_THRESHOLD ? DIFFICULTY_DX : DIFFICULTY_STD;
  return table[level] ?? `Unknown(${level})`;
}

function sumJudgement(entry, suffix) {
  let total = 0;
  for (const noteType of NOTE_TYPES) {
    total += entry[`${noteType}${suffix}`] ?? 0;
  }
  return total;
}

function nonCritBreakCount(entry) {
  let total = 0;
  for (const key of ["breakPerfect", "breakGreat", "breakGood", "breakMiss"]) {
    total += entry[key] ?? 0;
  }
  return total;
}

function getLamp(entry) {
  const isAp = entry.isAllPerfect ?? false;
  const combo = entry.comboStatus ?? 0;
  const isFc = entry.isFullCombo ?? false;
  const isClear = entry.isClear ?? false;

  const great = sumJudgement(entry, "Great");
  const good = sumJudgement(entry, "Good");
  const miss = sumJudgement(entry, "Miss");
  const judgementAp =
    great + good + miss === 0 &&
    sumJudgement(entry, "CriticalPerfect") + sumJudgement(entry, "Perfect") > 0;

  if (isAp || judgementAp) {
    return nonCritBreakCount(entry) === 0 ? "ALL PERFECT+" : "ALL PERFECT";
  }
  if (combo >= 2) return "FULL COMBO+";
  if (combo >= 1 || isFc) return "FULL COMBO";
  if (isClear) return "CLEAR";
  return "FAILED";
}

/**
 * Parse userPlayDate to unix seconds (UTC), matching the Python converter.
 * Legacy: "YYYY-MM-DD HH:MM:SS[.f]". Newer: ISO-8601 (often with trailing Z).
 * The Z does not mean true UTC — buildSessionOffsets recovers the shift.
 */
function parseUserPlayDate(dateStr) {
  if (!dateStr) return null;
  if (typeof dateStr === "string" && dateStr.includes("T")) {
    let iso = dateStr;
    if (dateStr.endsWith("Z")) {
      iso = dateStr.slice(0, -1) + "+00:00";
    } else if (!/[+-]\d{2}:\d{2}$/.test(dateStr)) {
      // Naive ISO → treat as UTC, like Python replace(tzinfo=timezone.utc)
      iso = dateStr + "+00:00";
    }
    const ms = Date.parse(iso);
    if (!Number.isNaN(ms)) return Math.trunc(ms / 1000);
  }
  const m = /^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?$/.exec(
    dateStr
  );
  if (m) {
    const ms = Date.UTC(
      Number(m[1]),
      Number(m[2]) - 1,
      Number(m[3]),
      Number(m[4]),
      Number(m[5]),
      Number(m[6]),
      0
    );
    return Math.trunc(ms / 1000);
  }
  return null;
}

function buildSessionOffsets(playlogs) {
  const earliest = new Map();
  for (const entry of playlogs) {
    const login = entry.loginDate;
    if (login == null) continue;
    const upd = parseUserPlayDate(entry.userPlayDate);
    if (upd == null) continue;
    if (!earliest.has(login) || upd < earliest.get(login)) {
      earliest.set(login, upd);
    }
  }
  const offsets = new Map();
  for (const [login, upd] of earliest) {
    let raw = upd - login;
    if (raw < 0) raw = 0;
    offsets.set(login, Math.floor(raw / 3600) * 3600);
  }
  return offsets;
}

function getTimeAchieved(entry, sessionOffsets) {
  const login = entry.loginDate;
  if (login == null) return null;
  const upd = parseUserPlayDate(entry.userPlayDate);
  const offset = sessionOffsets.get(login);
  if (upd != null && offset != null) {
    return (upd - offset) * 1000;
  }
  return login * 1000;
}

function tachiRejectReason(score) {
  const percent = score.percent;
  const lamp = score.lamp;
  const judgements = score.judgements || {};
  const optional = score.optional || {};

  if (lamp === "ALL PERFECT+" && percent !== 101) {
    return `ALL PERFECT+ requires 101% (got ${percent})`;
  }
  if (lamp !== "ALL PERFECT+" && percent === 101) {
    return `101% must be ALL PERFECT+ (got lamp=${lamp})`;
  }
  if (lamp === "ALL PERFECT" && percent < 100.5) {
    return `ALL PERFECT requires >= 100.5% (got ${percent})`;
  }
  if (lamp === "CLEAR" && percent < 80) {
    return `CLEAR requires >= 80% (got ${percent})`;
  }
  if (lamp === "FAILED" && percent >= 80) {
    return `FAILED requires < 80% (got ${percent})`;
  }

  const great = judgements.great;
  const good = judgements.good;
  const miss = judgements.miss;
  if (great != null && good != null && miss != null) {
    if (
      (lamp === "ALL PERFECT+" || lamp === "ALL PERFECT") &&
      great + good + miss > 0
    ) {
      return `${lamp} with non-perfect judgements`;
    }
    if (lamp === "FULL COMBO+" && good + miss > 0) {
      return "FULL COMBO+ with goods or misses";
    }
    if (lamp === "FULL COMBO" && miss > 0) {
      return "FULL COMBO with misses";
    }
  }

  const maxCombo = optional.maxCombo;
  const pcrit = judgements.pcrit;
  const perfect = judgements.perfect;
  if (
    maxCombo != null &&
    pcrit != null &&
    perfect != null &&
    great != null &&
    good != null &&
    miss != null &&
    lamp !== "CLEAR" &&
    lamp !== "FAILED" &&
    pcrit + perfect + great + good + miss !== maxCombo
  ) {
    return `${lamp} maxCombo != sum of judgements`;
  }

  return null;
}

function convertPlaylogEntry(entry, sessionOffsets) {
  const musicId = entry.musicId;
  const level = entry.level;
  const achievement = entry.achievement;

  if (level === UTAGE_LEVEL) {
    return {
      score: null,
      reason: `Utage (musicId=${musicId}, level=10) — not supported by Tachi`,
    };
  }

  const difficulty = getDifficulty(musicId, level);
  if (difficulty.startsWith("Unknown(")) {
    return {
      score: null,
      reason: `unsupported difficulty ${difficulty} (musicId=${musicId})`,
    };
  }

  const score = {
    percent: achievement / 10000.0,
    lamp: getLamp(entry),
    matchType: "inGameID",
    identifier: String(musicId),
    difficulty,
  };

  const ts = getTimeAchieved(entry, sessionOffsets);
  if (ts != null) {
    score.timeAchieved = ts;
  }

  score.judgements = {
    pcrit: sumJudgement(entry, "CriticalPerfect"),
    perfect: sumJudgement(entry, "Perfect"),
    great: sumJudgement(entry, "Great"),
    good: sumJudgement(entry, "Good"),
    miss: sumJudgement(entry, "Miss"),
  };

  const optional = {};
  if ("fastCount" in entry && entry.fastCount != null) {
    optional.fast = entry.fastCount;
  }
  if ("lateCount" in entry && entry.lateCount != null) {
    optional.slow = entry.lateCount;
  }
  if ("maxCombo" in entry && entry.maxCombo != null) {
    optional.maxCombo = entry.maxCombo;
  }
  if (Object.keys(optional).length > 0) {
    score.optional = optional;
  }

  const reject = tachiRejectReason(score);
  if (reject) {
    return { score: null, reason: `musicId=${musicId}: ${reject}` };
  }

  return { score, reason: null };
}

function skipCategory(reason) {
  if (reason.startsWith("Utage")) return "Utage (level 10)";
  if (reason.startsWith("unsupported difficulty")) return "unsupported difficulty";
  return "Tachi validator reject";
}

function convertPlaylogs(playlogs) {
  const sessionOffsets = buildSessionOffsets(playlogs);
  const scores = [];
  const skipCategories = new Map();
  const skipDetails = [];

  for (const entry of playlogs) {
    const { score, reason } = convertPlaylogEntry(entry, sessionOffsets);
    if (score == null) {
      const cat = skipCategory(reason);
      skipCategories.set(cat, (skipCategories.get(cat) || 0) + 1);
      skipDetails.push(reason);
      continue;
    }
    scores.push(score);
  }

  return { scores, skipCategories, skipDetails };
}

/**
 * Convert a parsed MuNET All Data JSON object to Tachi BATCH-MANUAL.
 * @returns {{ batchManual: object, scores: object[], skipCategories: [string, number][], skipDetails: string[] }}
 */
function convertMunetData(data) {
  const playlogs = data.userPlaylogList || [];
  const { scores, skipCategories, skipDetails } = convertPlaylogs(playlogs);

  const skipList = [...skipCategories.entries()].sort((a, b) => b[1] - a[1]);

  const batchManual = {
    meta: {
      game: "maimaidx",
      playtype: "Single",
      service: "MuNET",
    },
    scores,
  };

  return { batchManual, scores, skipCategories: skipList, skipDetails };
}

export { convertMunetData, parseUserPlayDate };
