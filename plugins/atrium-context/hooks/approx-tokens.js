// A rough token count for text handed to the model: about four characters a
// token for English prose. An estimate for the details pane, not a bill.
export function approxTokens(chars) {
  return Math.ceil(chars / 4)
}
