export function calcEMA(data, period) {
  const ema = [];
  if (data.length === 0) return [];
  const k = 2 / (period + 1);
  let prevEma = data[0].close;
  ema.push({ time: data[0].time, value: prevEma });
  for (let i = 1; i < data.length; i++) {
    const val = data[i].close * k + prevEma * (1 - k);
    ema.push({ time: data[i].time, value: val });
    prevEma = val;
  }
  return ema;
}

export function calcBollingerBands(data, period = 20, multiplier = 2) {
  const upper = [];
  const middle = [];
  const lower = [];
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      middle.push({ time: data[i].time, value: data[i].close });
      upper.push({ time: data[i].time, value: data[i].close });
      lower.push({ time: data[i].time, value: data[i].close });
      continue;
    }
    let sum = 0;
    for (let j = 0; j < period; j++) {
      sum += data[i - j].close;
    }
    const mean = sum / period;
    let variance = 0;
    for (let j = 0; j < period; j++) {
      variance += Math.pow(data[i - j].close - mean, 2);
    }
    const stdDev = Math.sqrt(variance / period);
    middle.push({ time: data[i].time, value: mean });
    upper.push({ time: data[i].time, value: mean + multiplier * stdDev });
    lower.push({ time: data[i].time, value: mean - multiplier * stdDev });
  }
  return { upper, middle, lower };
}

export function calcRSI(data, period = 14) {
  const rsi = [];
  if (data.length < period) return [];
  
  let gains = 0;
  let losses = 0;
  
  for (let i = 1; i <= period; i++) {
    const diff = data[i].close - data[i - 1].close;
    if (diff > 0) gains += diff;
    else losses -= diff;
  }
  
  let avgGain = gains / period;
  let avgLoss = losses / period;
  let rs = avgGain / (avgLoss || 1e-10);
  rsi.push({ time: data[period].time, value: 100 - (100 / (1 + rs)) });
  
  for (let i = period + 1; i < data.length; i++) {
    const diff = data[i].close - data[i - 1].close;
    const gain = diff > 0 ? diff : 0;
    const loss = diff < 0 ? -diff : 0;
    
    avgGain = (avgGain * (period - 1) + gain) / period;
    avgLoss = (avgLoss * (period - 1) + loss) / period;
    rs = avgGain / (avgLoss || 1e-10);
    rsi.push({ time: data[i].time, value: 100 - (100 / (1 + rs)) });
  }
  return rsi;
}

export function calcMACD(data, fast = 12, slow = 26, signal = 9) {
  if (!data || data.length === 0) return { macdLine: [], signalLine: [], histogram: [] };
  const emaFast = calcEMA(data, fast);
  const emaSlow = calcEMA(data, slow);
  
  const macdLine = [];
  for (let i = 0; i < data.length; i++) {
    const fVal = emaFast[i]?.value ?? data[i].close;
    const sVal = emaSlow[i]?.value ?? data[i].close;
    macdLine.push({ time: data[i].time, value: fVal - sVal });
  }
  
  const signalLine = [];
  const k = 2 / (signal + 1);
  let prevEma = macdLine[0].value;
  signalLine.push({ time: macdLine[0].time, value: prevEma });
  for (let i = 1; i < macdLine.length; i++) {
    const val = macdLine[i].value * k + prevEma * (1 - k);
    signalLine.push({ time: macdLine[i].time, value: val });
    prevEma = val;
  }
  
  const histogram = [];
  for (let i = 0; i < macdLine.length; i++) {
    histogram.push({
      time: macdLine[i].time,
      value: macdLine[i].value - (signalLine[i]?.value || 0)
    });
  }
  
  return { macdLine, signalLine, histogram };
}
