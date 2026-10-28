"""OCR backend for private statement screenshots and scanned PDF pages."""
from functools import lru_cache
from statistics import mean


@lru_cache(maxsize=1)
def _engine():
    from rapidocr import RapidOCR
    return RapidOCR()


def ocr_lines(data):
    result = _engine()(data)
    txts = list(result.txts) if result.txts is not None else []
    boxes = list(result.boxes) if result.boxes is not None else []
    scores = list(result.scores) if result.scores is not None else []
    if not txts:
        raise ValueError("No readable text was found in this image.")
    if not boxes or len(boxes) != len(txts):
        return "\n".join(txts), int(mean(scores)*100) if scores else 65
    items = []
    heights = []
    fallback_scores = scores if len(scores)==len(txts) else [0.7]*len(txts)
    for text, box, score in zip(txts, boxes, fallback_scores):
        xs = [float(point[0]) for point in box]
        ys = [float(point[1]) for point in box]
        items.append((sum(ys)/len(ys), min(xs), str(text), float(score)))
        heights.append(max(ys)-min(ys))
    tolerance = max(8.0, (sum(heights)/len(heights))*0.65) if heights else 12.0
    groups = []
    for item in sorted(items,key=lambda value:(value[0],value[1])):
        if not groups or abs(item[0]-groups[-1][0][0]) > tolerance:
            groups.append([item])
        else:
            groups[-1].append(item)
    lines = [" ".join(value[2] for value in sorted(group,key=lambda value:value[1])) for group in groups]
    confidence = int(mean(value[3] for value in items)*100) if items else 65
    return "\n".join(lines), confidence
