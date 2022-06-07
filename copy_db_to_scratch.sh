#!/bin/bash
#SBATCH -t 48:00:00
#SBATCH -p owners
#SBATCH -n 16

ml system mpifileutils

if [ $# -eq 0 ]
  then
    echo "No arguments supplied. Copying default AF data from OAK to GROUP_SCRATCH"
    srun dcp /oak/stanford/groups/deissero/projects/alphafold /scratch/groups/deissero/projects
elif [ $# -eq 1 ]
  then
    echo "Alternative source directory argument supplied. Copying AF data to GROUP_SCRATCH with source directory=$1"
    srun dcp $1 /scratch/groups/deissero/projects
else
    printf "Error: invalid arguments. Exiting" >&2
    exit 1
fi
