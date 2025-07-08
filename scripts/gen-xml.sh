#!/bin/bash
# gen-xml.sh

generate_mac() {
  printf "52:54:00:%02x:%02x:%02x\n" $((RANDOM%256)) $((RANDOM%256)) $((RANDOM%256))
}

# Check if the base XML file exists
if [ ! -f "alpine.xml" ]; then
  echo "Error: Base XML file 'alpine.xml' not found."
  exit 1
fi

# Read the base XML file
base_xml=$(cat alpine.xml)

# Make sure the XML has the QEMU namespace defined
if ! grep -q "xmlns:qemu=\"http://libvirt.org/schemas/domain/qemu/1.0\"" alpine.xml; then
  echo "Adding QEMU namespace to XML template..."
  base_xml=$(echo "$base_xml" | sed 's|<domain type="kvm"|<domain type="kvm" xmlns:qemu="http://libvirt.org/schemas/domain/qemu/1.0"|')
fi

# Get the absolute path to the current directory for disk images
disk_path=$(realpath .)

# Generate XML files for each VM
for i in 1 2 3; do
  # Generate unique identifiers
  uuid=$(uuidgen)
  mac=$(generate_mac)

  # Set output filenames
  xml_file="alpine-vm-$i.xml"
  qcow2_file="$disk_path/alpine-$i.qcow2"
  ssh_port=$((2221 + i))  # 2222, 2223, 2224

  # Create the modified XML
  modified_xml=$(echo "$base_xml" | \
    sed "s|<name>grs-project-1</name>|<name>grs-project-$i</name>|g" | \
    sed "s|<uuid>.*</uuid>|<uuid>$uuid</uuid>|g" | \
    sed "s|<mac address=\"[^\"]*\"/>|<mac address=\"$mac\"/>|g" | \
    sed "s|<source file=\"[^\"]*\"/>|<source file=\"$qcow2_file\"/>|g")

  # Handle QEMU commandline for port forwarding
  if grep -q "<qemu:commandline>" <<< "$modified_xml"; then
    # Replace existing port forwarding
    modified_xml=$(echo "$modified_xml" | \
      sed "s|hostfwd=tcp::[0-9]*-:22|hostfwd=tcp::$ssh_port-:22|g")
  else
    # Add new port forwarding section
    modified_xml=$(echo "$modified_xml" | \
      sed "s|</devices>|</devices>\n  <qemu:commandline>\n    <qemu:arg value='-netdev'/>\n    <qemu:arg value='user,id=net0,hostfwd=tcp::$ssh_port-:22'/>\n  </qemu:commandline>|g")
  fi

  # Write the modified XML to the output file
  echo "$modified_xml" > "$xml_file"

  echo "Created $xml_file with:"
  echo "  - Name: grs-project-$i"
  echo "  - UUID: $uuid"
  echo "  - MAC: $mac"
  echo "  - Disk: $qcow2_file"
  echo "  - SSH Port: $ssh_port"
  echo
done

echo "XML files generated successfully."
echo "Next steps:"
echo "1. Stop any running VMs with 'virsh destroy grs-project-1', etc."
echo "2. Undefine existing VMs (if any) with 'virsh undefine grs-project-1', etc."
echo "3. Define the new VMs with 'virsh define alpine-vm-1.xml', etc."
echo "4. Start the VMs with 'virsh start grs-project-1', etc."
echo "5. Verify SSH ports are open with 'netstat -tuln | grep 222'"
