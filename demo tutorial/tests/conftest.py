import os
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
TESTS = Path(__file__).resolve().parent
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))


def _spark_available() -> bool:
    try:
        import delta  # noqa: F401
        import pyspark  # noqa: F401
    except ImportError:
        return False
    return bool(os.environ.get("JAVA_HOME"))


@pytest.fixture(scope="session")
def spark(tmp_path_factory):
    """Local Spark 3.5 + Delta session, mirroring Fabric Runtime 1.3.

    On Windows, set ZAVA_TEST_CLASSPATH to the Delta jars plus a test-only local
    file-system jar (see tests/README.md). Spark tests are skipped when unavailable.
    """
    if not _spark_available():
        pytest.skip("Spark/Delta runtime with JAVA_HOME is not available")
    from pyspark.sql import SparkSession

    work = tmp_path_factory.mktemp("spark")
    builder = (SparkSession.builder.master("local[4]").appName("zava-ssot-notebook-tests")
               .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
               .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
               .config("spark.sql.warehouse.dir", str(work / "warehouse"))
               .config("spark.sql.shuffle.partitions", "2")
               .config("spark.databricks.delta.snapshotPartitions", "2")
               .config("spark.default.parallelism", "2")
               .config("spark.ui.enabled", "false")
               .config("spark.driver.memory", os.environ.get("ZAVA_TEST_DRIVER_MEMORY", "4g"))
               .config("spark.sql.ui.retainedExecutions", "5")
               .config("spark.ui.retainedJobs", "50")
               .config("spark.ui.retainedStages", "50")
               .config("spark.ui.showConsoleProgress", "false")
               .config("spark.sql.session.timeZone", "UTC")
               .config("spark.driver.extraJavaOptions", "-Duser.timezone=UTC"))
    classpath = os.environ.get("ZAVA_TEST_CLASSPATH")
    if classpath:
        builder = (builder.config("spark.driver.extraClassPath", classpath)
                   .config("spark.hadoop.fs.file.impl", "localtest.NoPermissionLocalFileSystem")
                   .config("spark.hadoop.fs.AbstractFileSystem.file.impl", "localtest.NoPermissionLocalFs"))
        session = builder.getOrCreate()
    else:
        from delta import configure_spark_with_delta_pip

        session = configure_spark_with_delta_pip(builder).getOrCreate()
    session.sparkContext.setLogLevel("ERROR")
    yield session
    session.stop()
    shutil.rmtree(work, ignore_errors=True)
