"""Script to launch an alphafold SLURM job the D-Lab way."""

import argparse
import logging
import os
import shlex
import subprocess


def main(fasta_paths,
         output_dir, 
         max_template_date, 
         db_preset, 
         model_preset,
         num_multimer_predictions_per_model,
         job_name, 
         partition, 
         time, 
         constraint,
         container_path, 
         data_dir, 
         ssd_data_dir,
         log_only):

    log_dir = os.path.join(output_dir, "logs")
    logging.info("Logging directory:\n%s", log_dir)

    slurm_output_path = os.path.join(log_dir, "slurm-%j.out")
    logging.info("SLURM output path (%%j=job_id):\n%s", slurm_output_path)

    # mem-per-cpu: Found that asking for 8GB on systems with 8GB per core may 
    #              "round up" and take 2x the requested cores.
    slurm_args = [
        "--job-name", job_name,
        "--time", time,
        "--partition", partition,
        "--constraint", constraint,
        "--cpus-per-task", "16",
        "--mem-per-cpu", "15GB",
        "--gpus", "1",
        "--output", slurm_output_path,
    ]

    singularity_command = [
        "singularity", "run",
        "--nv", "--pwd", "/app/alphafold",
        container_path
    ]

    script_path = os.path.join(output_dir, f"{job_name}.sbatch")
    logging.info("Script path:\n%s", script_path)
    
    alphafold_dlab_args = [
        "--fasta_paths", fasta_paths,
        "--output_dir", output_dir,
        "--data_dir", data_dir,
        "--ssd_data_dir", ssd_data_dir,
        "--max_template_date", max_template_date,
        "--db_preset", db_preset,
        "--model_preset", model_preset,
        "--num_multimer_predictions_per_model", num_multimer_predictions_per_model,
        "--log_dir", log_dir,
    ]


    script_command = singularity_command + alphafold_dlab_args
    # shlex join requires python 3.8
    # script_command_quoted = shlex.join(script_command)
    script_command_quoted = ' '.join(shlex.quote(x) for x in script_command)
    logging.info("Script command:\n%s", script_command_quoted)

    slurm_command = ["sbatch"] + slurm_args + [script_path]
    logging.info("Slurm command list:\n%s", slurm_command)

    if log_only:
        return

    os.makedirs(full_output_dir, exist_ok=False)
    os.makedirs(log_dir)

    script_text = f"""#!/bin/bash
{script_command_quoted}
"""

    with open(script_path, "w") as f:
        f.write(script_text)

    subprocess.run(slurm_command, check=True)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Launch alphafold on SLURM")
    parser.add_argument("--fasta_paths", required=True,
                        help="Fasta files to process (basenames should be unique)")
    parser.add_argument("--output_dir", required=True,
                        help="Directory within which to create subdirectories for output (one per fasta_path)")
    parser.add_argument("--max_template_date", required=True,
                        help="Maximum template release date to consider. Important if folding historical test sets.")
    parser.add_argument("--db_preset", required=True, choices=['reduced_dbs', 'full_dbs'],
                        help="Preset db configuration (see Alphafold docs)")
    parser.add_argument("--model_preset", required=True, choices=['monomer', 'monomer_casp14', 'monomer_ptm', 'multimer'],
                        help="Preset model configuration (see Alphafold docs)")
    parser.add_argument("--num_multimer_predictions_per_model", required=False, default=5,
                        help="How many predictions (each with a different random seed) will be "
                        "generated per model. E.g. if this is 2 and there are 5 "
                        "models then there will be 10 predictions per input. "
                        "Note: this FLAG only applies if model_preset=multimer")
    parser.add_argument("--alternative_data_dir",  default=None, required=False,
                        help="Path to directory of the supporting model data. "
                        "If None, defaults to GROUP_SCRATCH/projects/alphafold/model_data")
    parser.add_argument("--alternative_container",  default=None, required=False,
                        help="Path to an alternative docker image (.sif) for use with singularity"
                        "If None, defaults to GROUP_HOME/projects/alphafold/singularity/alphafold.sif")

    parser.add_argument("--job_name", required=True, help="SLURM job_name")
    parser.add_argument("--partition", default="owners", help="SLURM partition")
    parser.add_argument("--time", default="48:00:00", help="Expected SLURM job time")
    parser.add_argument("--use_local_ssd", default=False, action="store_true",
                        help="Whether to use local ssd to speed up sequence searches at the cost of"
                        "running a time-consuming copy job of the databases and constraints on which"
                        "CPUs can be used (RME CPUs)")
    parser.add_argument("--constraint", default="GPU_SKU:A100_PCIE|GPU_SKU:A100_SXM4",
                        help="SLURM jobs constraint")
    parser.add_argument("--log_only", default=False, action="store_true",
                        help="Do not submit to slurm, only log commands. Useful for debugging.")

    args = parser.parse_args()

    # Locations specific to the D-Lab
    group_home = os.environ["GROUP_HOME"]
    group_scratch = os.environ['GROUP_SCRATCH']
    ssd_scratch = os.environ['L_SCRATCH']

    if args.alternative_container:
        container_path = os.path.realpath(args.alternative_container)
    else:
        container_path = os.path.join(group_home, "projects", "alphafold", "singularity", "alphafold.sif")
        container_path = os.path.realpath(container_path)

    version = os.path.splitext(os.path.basename(container_path))[0]
    output_subdir = f"{version}__max_template_date_{args.max_template_date}__db_preset_{args.db_preset}__model_preset_{args.model_preset}"
    full_output_dir = os.path.join(args.output_dir, output_subdir, args.job_name)

    if args.alternative_data_dir:
        data_dir = os.path.realpath(args.alternative_data_dir)
    else:
        data_dir = os.path.join(group_scratch, "projects", "alphafold", "model_data")

    if args.use_local_ssd:
        # There is no constraint to use nodes with large SSD, so instead use the
        # RME cpu constraint.  RME cpus are on machines with large local SSD.
        ssd_dir = os.path.join(ssd_scratch, "model_data")
        constraints = f"({args.constraint})&CPU_GEN:RME"
    else:
        ssd_dir = ''
        constraints = args.constraint

    main(fasta_paths=args.fasta_paths,
         output_dir=full_output_dir,
         max_template_date=args.max_template_date,
         db_preset=args.db_preset,
         model_preset=args.model_preset,
         job_name=args.job_name,
         partition=args.partition,
         time=args.time,
         constraint=constraints,
         container_path=container_path,
         data_dir=data_dir,
         num_multimer_predictions_per_model=args.num_multimer_predictions_per_model,
         ssd_data_dir=ssd_dir,
         log_only=args.log_only)
