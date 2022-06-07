# AlphaFold on Sherlock

The [`dlab-sherlock-multimer`](https://github.com/deisseroth-lab/alphafold/tree/dlab-sherlock-multimer)
contains update and scripts to run AF v2.2 (merged from deepmind/alphafold main, 1 June 2022) on Stanford's Sherlock cluster.

## Quick Start

You should be familiar the important command-line flags:
`max_template_date`, `model_preset`, `db_preset`, and `fasta_paths`.
For details on these flags see the
[AF docs](https://github.com/deepmind/alphafold/blob/main/README.md#running-alphafold)  


From within your clone of the alphafold repo on Sherlock (replace uppercase with real paths):

```sh
python3 /ABS_PATH_TO_CLONED_REPO/run_alphafold_dlab_slurm.py \
    --max_template_date 2100-01-01 \
    --model_preset monomer \
    --db_preset full_dbs \
    --fasta_paths ABS_PATH_TO_FIRST_FASTA/protein0.fasta [, ABS_PATH_TO_SECOND_FASTA/protein1.fasta, ...] \
    --output_dir ABS_PATH_TO_OUTPUT_DIR \
    --job_name twoproteins 
```

The output will be stored in a directory denoting the D-Lab alphafold software version used, and the
flags used. For the command above, this would be:

```sh
<output_dir>/alphafold_2022.6.0__max_template_date_2100-01-01__db_preset_full_dbs__model_preset_monomer/twoproteins
```

Within that directory there will be:

- A subdirectory for each fasta file containing the AlphaFold prediction information the protein sequence.
- The script, named `<job_name>.sbatch`, which was submitted to the Sherlock SLURM scheduler.
- A logs subdirectory containing any output logs from the job.  Currently this a single file with the
  SLURM job's stdout and stderr.

## Changes for SLURM

The more pertinent changes to run AF on Sherlock:

- Update Dockerfile to use `HAVE_AVX2=1` compile flag, so that it will run on AMD CPUs within the cluster,
  even if built on an Intel CPU with additional functionality.  This turns off AVX512.  
  The Dockerfile also adds the [rclone](https://rclone.org/) utility for fast data copies.
- Build rules for a Singularity image (via a Docker image).  There is a [Makefile](Makefile) to aid in this process,
  which builds the image in the `/tmp/alphafold` directory.
- Add [run_alphafold_dlab.py](run_alphafold_dlab.py) to unify input data paths and
  optionally copy high IOPS databases to local SSD before starting predictions.  Under the hood, this script
  uses [run_alphafold.py](run_alphafold.py).  Advanced users can run this interactively on a node.
- Add [run_alphafold_dlab_slurm.py](run_alphafold_dlab_slurm.py) (a python3.6 compatible script with no
  dependencies) to launch a SLURM job that will execute [run_alphafold_dlab.py](run_alphafold_dlab.py)
  using the default Singularity container.  This is the main driver script most users will use.

## Building new Singularity image

To create a new version, once must use a non-Sherlock machine.   This is because Sherlock does not give root
access, which is needed to build intermediate Docker images.  To release a new software version: tag the
repo with the version, run make, and then copy the output to our group space.  Versioning uses the
[CalVer](https://calver.org/) YYYY.MM.MICRO syntax: year, month, and monthly release number. Do not forget that new AF 
versions might also require modifications to our scripts (beyond merging) and to the model data used by AF.

Example release, on a non-Sherlock machine:
```sh
git tag 2022.6.0
make
scp /tmp/alphafold/2022.6.0-dirty.sif sherlock:/home/groups/deissero/projects/alphafold/singularity
```
Now you should test that the new version successfully predicts both monomers and multimers by running something like:
```sh
python3 /ABS_PATH_TO_CLONED_REPO/run_alphafold_dlab_slurm.py \
    --alternative_container $GROUP_HOME/projects/alphafold/singularity/2022.6.0-dirty.sif \
    --alternative_data_dir /ABS_PATH_MODEL_DATA_FOR_NEW_VERSION/model_data \
    --max_template_date 2100-01-01 \
    --model_preset monomer \
    --db_preset full_dbs \
    --fasta_paths /ABS_PATH_TO_CLONED_REPO/test_fastas/6I9K_monomer.fasta \
    --output_dir $OAK/users/$USER/alphafold/output \
    --job_name test_mono
```
```sh
python3 /ABS_PATH_TO_CLONED_REPO/run_alphafold_dlab_slurm.py \
    --alternative_container $GROUP_HOME/projects/alphafold/singularity/2022.6.0-dirty.sif \
    --alternative_data_dir /ABS_PATH_MODEL_DATA_FOR_NEW_VERSION/model_data \
    --max_template_date 2100-01-01 \
    --model_preset multimer \
    --db_preset full_dbs \
    --fasta_paths /ABS_PATH_TO_CLONED_REPO/test_fastas/6I9K_homodimer.fasta \
    --output_dir $OAK/users/$USER/alphafold/output \
    --job_name test_multi 
```

After testing that the new version successfully predicts both monomers and multimers, you make it the default version by updating the symlink on a Sherlock machine:

```sh
cd $GROUP_HOME/projects/alphafold/singularity/
mv alphafold_2022.6.0-dirty.sif alphafold_2022.6.0.sif
ln -sf alphafold_2022.6.0.sif alphafold.sif
```

## Keep database and model data on GROUP_SCRATCH

The GROUP_SCRATCH is purged of files not created in the last 90 days.  To recopy the files, use the script 
copy_db_to_scratch.sh, located in this repository:

```sh
sbatch /PATH_TO_LOCAL_REPO_CLONE/copy_db_to_scratch.sh 
```
This job could take a few hours. 

If you want to clone a new/different version of AF to GROUP_SCRATCH, you can run something like:

```sh
sbatch /PATH_TO_LOCAL_REPO_CLONE/copy_db_to_scratch.sh /oak/stanford/groups/deissero/projects/alphafold_new_version
```