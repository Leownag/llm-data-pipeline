"""Custom Dataset Builder for Common Crawl."""
import datasets
import pipeline
from warc_io import read_warc_file
from typing import List, Iterator, Tuple, Dict, Any

logger = datasets.logging.get_logger(__name__)

_DESCRIPTION = """\
MiniCleanedCommonCrawl is a single WARC shard of the CC-MAIN-2018-17 Common Crawl dump that
has been converted from raw HTML to plain text, stripped of low-quality paragraphs, masked for
personally identifiable information, and filtered with a Gopher/RedPajama-style heuristic
quality classifier. Each example is a crawled URL and its cleaned document text."""
_DATA_URL = "https://data.commoncrawl.org/crawl-data/CC-MAIN-2018-17/segments/1524125937193.1/warc/CC-MAIN-20180420081400-20180420101400-00000.warc.gz"

class MiniCleanedCommonCrawl(datasets.GeneratorBasedBuilder):
    def _info(self) -> datasets.DatasetInfo:
        """
        Should return a DatasetInfo object describing <string> type values for a url and it's corresponding text.
        """
        return datasets.DatasetInfo(
            description=_DESCRIPTION,
            features=datasets.Features({
                "url": datasets.Value("string"),
                "text": datasets.Value("string"),
            }),
            supervised_keys=None,
            homepage="https://commoncrawl.org/",
        )

    def _split_generators(self, dl_manager: datasets.DownloadManager) -> List[datasets.SplitGenerator]:
        """
        Should return a SplitGenerator object which downloads your data and creates train and validation splits.
        """
        archive = dl_manager.download_and_extract(_DATA_URL)
        return [
            datasets.SplitGenerator(
                name=datasets.Split.TRAIN,
                gen_kwargs={"filepaths": [archive]},
            )
        ]

    def _generate_examples(self, filepaths: List[str]) -> Iterator[Tuple[Any, Dict[str, str]]]:
        """
        Streams raw data from the downloaded file and yields tuples consisting of a unique ID and the url/cleaned text.
        Should call the functions you defined in homework.py.
        """
        key = 0
        for filepath in filepaths:
            logger.info("generating examples from = %s", filepath)
            for url, html in read_warc_file(filepath):
                cleaned = pipeline.clean_text(pipeline.html_to_text(html))
                # Quality first: replace_pii emits "XXX", which is itself in the bad-word list.
                if pipeline.heuristic_quality_filter(cleaned):
                    yield key, {"url": url, "text": pipeline.replace_pii(cleaned)}
                    key += 1

if __name__ == "__main__":
    # Note: Calling load_dataset caches the processed dataset locally.
    # The default cache directory is ~/.cache/huggingface/datasets.
    # To force the dataset to be recreated, you should pass in the
    # additional argument download_mode=datasets.DownloadMode.REUSE_CACHE_IF_EXISTS
    dataset = datasets.load_dataset(
        "mini_ccc.py",
        "MiniCleanedCommonCrawl",
        trust_remote_code=True,
        split=datasets.Split.TRAIN)

    # Iterate over the first 100 examples.
    for ex in dataset.take(100):
        print(ex["url"])
